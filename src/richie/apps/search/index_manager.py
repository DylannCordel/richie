"""
ElasticSearch indexes utilities.
"""
from functools import reduce

from django.conf import settings
from django.utils import timezone
from django.utils.module_loading import import_string

from elasticsearch.client import IndicesClient
from elasticsearch.exceptions import NotFoundError
from elasticsearch.helpers import bulk


def get_indexable_from_string(indexable_module_string):
    """
    Load the indexable from the module.Class path in settings
    NB: we need this level of indirection to enable testing.
    """
    return import_string(indexable_module_string)


def get_indexes_by_alias(existing_indexes, alias):
    """
    Get existing index(es) for an alias. Support multiple existing aliases so the command
    always 'cleans up' the aliases even if they got messed up somehow.
    """
    for index, details in existing_indexes.items():
        if alias in details.get("aliases", {}):
            yield index, alias


def perform_create_index(indexable, logger):
    """
    Create a new index in ElasticSearch from an indexable instance
    """
    indices_client = IndicesClient(client=settings.ES_CLIENT)
    # Create a new index name, suffixing its name with a timestamp
    new_index = "{:s}_{:s}".format(
        indexable.index_name, timezone.now().strftime("%Y-%m-%d-%Hh%Mm%S.%fs")
    )

    # Create the new index
    logger.info('Creating a new Elasticsearch index "{:s}"...'.format(new_index))
    indices_client.create(index=new_index)
    indices_client.put_mapping(
        body=indexable.mapping, doc_type=indexable.document_type, index=new_index
    )

    # Populate the new index with data provided from our indexable class
    bulk(
        actions=indexable.get_data_for_es(new_index, "create"),
        chunk_size=settings.ES_CHUNK_SIZE,
        client=settings.ES_CLIENT,
        stats_only=True,
    )

    # Return the name of the index we just created in ElasticSearch
    return new_index


def regenerate_indexes(logger):
    """
    Create new indexes for our indexables and replace possible existing indexes with
    a new one only once it has successfully built it.
    """
    # Prepare the client we'll be using to handle indexes
    indices_client = IndicesClient(client=settings.ES_CLIENT)

    # Get all existing indexes once; we'll look up into this list many times
    try:
        existing_indexes = indices_client.get_alias("*")
    except NotFoundError:
        # Provide a fallback empty list so we don't have to check for its existence later on
        existing_indexes = []

    # Dynamically import the modules from the config mixin strings
    indexables = list(map(get_indexable_from_string, settings.ES_INDICES))

    # Create a new index for each of those modules
    # NB: we're mapping perform_create_index which produces side-effects
    indexes_to_create = zip(
        list(map(lambda ix: perform_create_index(ix, logger), indexables)), indexables
    )

    # Prepare to alias them so they can be swapped-in for the previous versions
    actions_to_create_aliases = [
        {"add": {"index": index, "alias": ix.index_name}}
        for index, ix in indexes_to_create
    ]

    # Get the previous indexes for every alias
    indexes_to_unalias = reduce(
        lambda acc, ix: acc
        + list(get_indexes_by_alias(existing_indexes, ix.index_name)),
        indexables,
        [],
    )

    # Prepare to un-alias them so they can be swapped-out for the new versions
    # NB: use chain to flatten the list of generators
    actions_to_delete_aliases = [
        {"remove": {"index": index, "alias": alias}}
        for index, alias in indexes_to_unalias
    ]

    # Identify orphaned indexes
    # NB: we *must* do this before the update_aliases call so we don't immediately prune
    # version n-1 of all our indexes
    useless_indexes = [
        index for index, details in existing_indexes.items() if "aliases" not in details
    ]

    # Replace the old indexes with the new ones in 1 atomic operation to avoid outage
    indices_client.update_aliases(
        dict(actions=actions_to_create_aliases + actions_to_delete_aliases)
    )

    # Cleanup step: do prune older indexes that are now useless
    for useless_index in useless_indexes:
        # Disable keyword arguments checking as elasticsearch-py uses a decorator to list
        # valid query parameters and inject them as kwargs. I won't say a word about this
        # anti-pattern.
        #
        # pylint: disable=unexpected-keyword-arg
        indices_client.delete(index=useless_index, ignore=[400, 404])
