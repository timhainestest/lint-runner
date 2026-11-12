name: release

on:
  workflow_dispatch:
    inputs:
      version:
        description: package version
        required: false
      ref:
        description: git ref to build
        required: false
      publish:
        description: publish to the index
        required: false
        type: boolean
        default: false

permissions:
  contents: read

jobs:
  build_wheels:
    name: Build sdist
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1 # v7.0.1
        with:
          ref: ${{ inputs.ref || github.ref }}
          persist-credentials: false
      - uses: actions/setup-python@5fda3b95a4ea91299a34e894583c3862153e4b97 # v7.0.0
        with:
          python-version: '3.11'
      - name: Build sdist
        env:
          BUILD_VERSION: ${{ inputs.version }}
        run: |
          pip install build
          python -m build --sdist --outdir dist
      - uses: actions/upload-artifact@043fb46d1a93c77aae656e7c1c64a875d1fc6a0a # v7.0.1
        with:
          name: dist
          path: dist/*.tar.gz

  publish_wheels:
    name: Publish to the index
    if: ${{ inputs.publish }}
    needs: build_wheels
    runs-on: ubuntu-latest
    steps:
      - uses: actions/download-artifact@9000827ccba6bdab643e8b6fd33ac0654aef8333 # v8.0.2
        with:
          name: dist
          path: dist
      - run: ls dist
      - name: Publish a Python distribution
        uses: pypa/gh-action-pypi-publish@ed0c53931b1dc9bd32cbe73a98c7f6766f8a527e # v1.13.0
        with:
          password: ${{ secrets.PYPI_API_TOKEN }}
          packages-dir: dist
          repository-url: ${{ vars.INDEX_URL }}
          verbose: true
