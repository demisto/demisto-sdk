const cli = require('commander');
const {readFile} = require('fs-extra');
const mdx = require('@mdx-js/mdx');

cli.version('0.1.0')
cli.requiredOption("-f --file <mdx file to parse>")
cli.parse(process.argv)

async function parseMDX(file) {
    const contents = await readFile(file, 'utf8');
    parsed = await mdx(contents)
    console.log(`${parsed}`)
}

parseMDX(cli.file).catch((reason) => {
    console.error(reason)
    process.exit(1)
})
