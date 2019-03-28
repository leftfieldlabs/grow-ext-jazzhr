# grow-ext-jazzhr

An extension to integrate Jazz HR data with Grow. Provides a way to
serialize Jazz HR jobs into YAML files.

## Concept

Jazz HR is an applicant tracking system and hiring tool for organizations to recruit and hire candidates. The Grow extension leverages the Jazz HR API so job listings can be embedded within a Grow website.

## Usage

### Grow setup

1. Create an `extensions.txt` file within your pod.
1. Add to the file: `git+git://github.com/leftfieldlabs/grow-ext-jazzhr`
1. Run `grow install`.
1. Add the following section to `podspec.yaml`:

```
extensions:
  preprocessors:
  - extensions.jazzhr.JazzhrPreprocessor

preprocessors:
- kind: jazzhr
  board_token: <token>
  jobs_collection: /content/jobs
```

The preprocessor accepts a few additional configuration options, see
`example/podspec.yaml` for examples.

### Configuration

1. Acquire the `api_token` from the
   (JazzHR Integrations page)[https://app.jazz.co/app/settings/integrations].

### Developer notes

- See [JazzHR API
  documentation](https://success.jazzhr.com/hc/en-us/articles/222540508-API-Overview) for more
  details.
