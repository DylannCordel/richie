const { GettextExtractor, JsExtractors, HtmlExtractors } = require('gettext-extractor');

let extractor = new GettextExtractor();

extractor
    .createJsParser([
        JsExtractors.callExpression('gt.gettext', {
            arguments: {
                text: 0,
                context: 1 
            }
        }),
    ])
    .parseFilesGlob('./fun_cms/**/*.@(ts|js|tsx|jsx)');

extractor.savePotFile('./messages.pot');

extractor.printStats();
