import { version, requiredOption, parse, file as _file } from 'commander';
import { readFile } from 'fs-extra';
import mdx from '@mdx-js/mdx';

version('0.1.0')
requiredOption("-f --file <mdx file to parse>")
parse(process.argv)

async function parseMDX(file) {
    const contents = await readFile(file, 'utf8');
    parsed = await mdx(contents)
    console.log(`${parsed}`)
}

parseMDX(_file).catch((reason) => {
    console.error(reason)
    process.exit(1)
})
