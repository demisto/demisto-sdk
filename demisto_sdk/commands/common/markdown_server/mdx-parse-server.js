
const http = require( 'http')
const mdx = require('@mdx-js/mdx');
const markdownlint = require( 'markdownlint')
const markdownlintRuleHelpers = require( 'markdownlint-rule-helpers' )
const url = require('url')


// explanation of the config can be found at
// https://github.com/DavidAnson/markdownlint/blob/main/schema/markdownlint-config-schema.json
const config = require( "./markdownlintconfig.js")

// explanation of the config can be found at
// https://github.com/DavidAnson/markdownlint/blob/main/schema/markdownlint-config-schema.json

function markdownLint(req, res, body, query) {

    let fileName = query.filename || 'readme'
    const fixOptions = {
      "config" : config,
      "strings": {
        [fileName] : body
      }
    };

    let validationResults = markdownlint.sync(fixOptions);

    let fixedText = null;

    if(query.fix && query.fix.toLowerCase() == 'true') {
        fixedText = body;
        const fixes = validationResults[fileName].filter(error => error.fixInfo);
        if (fixes.length > 0) {
            fixedText = markdownlintRuleHelpers.applyFixes(body, fixes);
            const fixOptions = {
                "config" : config,
                "strings": {
                    [fileName] : fixedText
                }
            };
            validationResults = markdownlint.sync(fixOptions)
        }
    }
    res.setHeader('Content-Type', 'application/json');
    res.statusCode = 200
    res.end(JSON.stringify({ validations : validationResults.toString(),
        fixedText : fixedText, errorNum : validationResults[fileName].length}))

}
function requestHandler(req, res) {
    // console.log(req)
    if (req.method != 'POST') {
        res.statusCode = 405
        res.end('Only POST is supported')
    }
    let body = ''
    req.setEncoding('utf8');
    req.on('data', function (data) {
        body += data
    })
    req.on('end', async function () {
        //   console.log('Body length: ' + body.length)

        let urlObj = url.parse(req.url, true)
        if(urlObj.pathname == '/markdownlint')
        {
            markdownLint(req, res, body, urlObj.query)
        }
        else {
            try {
                let parsed = await mdx(body)
                res.end('Successfully parsed mdx')
            } catch (error) {
                res.statusCode = 500
                res.end("MDX parse failure: " + error)
            }
        }

    })
}

const server = http.createServer(requestHandler);

server.listen(6161, (err) => {
    if (err) {
        return console.log('MDX server failed starting.', err)
    }
    console.log(`MDX server is listening on port: 6161`)
});
