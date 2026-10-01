import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import {
  ENDPOINT_OVERRIDE_KINDS,
  KIND_LABEL,
  PACKAGE_NAME,
  PACKAGE_VERSION,
  PROVIDER_KINDS,
} from '../lib/defaults.js'

const manifest = relative => JSON.parse(readFileSync(new URL(relative, import.meta.url), 'utf8'))

test('the package name and version agree with both manifests', () => {
  // The version is reported to the Python child as the MCP client version, so a
  // bump that misses one manifest would otherwise drift silently.
  for (const relative of ['../package.json', '../../../package.json']) {
    const { name, version } = manifest(relative)
    assert.equal(name, PACKAGE_NAME, relative)
    assert.equal(version, PACKAGE_VERSION, relative)
  }
})

test('every provider kind has a label, and only ddgs lacks an endpoint override', () => {
  for (const kind of PROVIDER_KINDS) {
    assert.equal(typeof KIND_LABEL[kind], 'string', `missing label for ${kind}`)
  }
  // `ddgs` drives the ddgs library and reads no endpoint variable, so the bridge
  // must not write one and the card must not offer the field.
  assert.equal(ENDPOINT_OVERRIDE_KINDS.includes('ddgs'), false)
  for (const kind of PROVIDER_KINDS) {
    if (kind === 'ddgs') continue
    assert.equal(ENDPOINT_OVERRIDE_KINDS.includes(kind), true, `expected an endpoint override for ${kind}`)
  }
})
