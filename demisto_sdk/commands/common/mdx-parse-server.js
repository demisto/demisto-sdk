import mdx from '@mdx-js/mdx';
import { createServer } from 'http';

function requestHandler(req, res) {
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
        try {
            parsed = await mdx(body)
            res.end('Successfully parsed mdx')
        } catch (error) {
            res.statusCode = 500
            res.end("MDX parse failure: " + error)
        }
    })
}

const server = createServer(requestHandler);

server.listen(6161, (err) => {
    if (err) {
        return console.log('MDX server failed starting.', err)
    }
    console.log(`MDX server is listening on port: 6161`)
});
