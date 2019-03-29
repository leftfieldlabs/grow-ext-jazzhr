from protorpc import messages
from protorpc import protojson
import bleach
import grow
import os
import requests
try:
    from HTMLParser import HTMLParser
except ImportError:
    from html.parser import HTMLParser


class Error(Exception):
    pass


class AttributeMessage(messages.Message):
    tag = messages.StringField(1)
    attributes = messages.StringField(2, repeated=True)


class JazzhrPreprocessor(grow.Preprocessor):
    KIND = 'jazzhr'
    JOBS_URL = 'https://api.resumatorapi.com/v1/jobs/status/open/confidential/false/private/false?apikey={api_key}'
    JOB_URL = 'https://api.resumatorapi.com/v1/jobs/{job_id}?apikey={api_key}'

    class Config(messages.Message):
        api_key = messages.StringField(1)
        jobs_collection = messages.StringField(2)
        allowed_html_tags = messages.StringField(4, repeated=True)
        allowed_html_attributes = messages.MessageField(AttributeMessage, 5, repeated=True)

    def bind_jobs(self, api_key, collection_path):
        url = JazzhrPreprocessor.JOBS_URL.format(api_key=api_key)
        resp = requests.get(url)
	if resp.status_code != 200:
            raise Error('Error requesting -> {}'.format(url))
        content = resp.json()
        self._bind(collection_path, content)

    def _parse_entry(self, item):
        if item.get('title'):
            item['$title'] = item.pop('title')
        if item.get('maximum_salary'):
            del item['maximum_salary']
        if item.get('minimum_salary'):
            del item['minimum_salary']
        if item.get('job_applicants'):
            del item['job_applicants']
        if item.get('content'):
            item['content'] = self._parse_content(item.get('content'))
        if item.get('compliance'):
            for i, row in enumerate(item['compliance']):
                item['compliance'][i]['description'] = \
                        self._parse_content(row['description'])
        return item

    def _parse_content(self, content):
        parser = HTMLParser()
        content = parser.unescape(content)
        tags = self.config.allowed_html_tags
        if tags:
            attributes = {}
            if self.config.allowed_html_attributes:
                for attribute in self.config.allowed_html_attributes:
                    attributes[attribute.tag] = attribute.attributes
            content = bleach.clean(
                    content, tags=tags, attributes=attributes, strip=True)
        return content

    def _get_single_job(self, item):
        api_key = self.config.api_key
        url = JazzhrPreprocessor.JOB_URL.format(
                api_key=api_key, job_id=item['id'])
        resp = requests.get(url)
	if resp.status_code != 200:
            raise Error('Error requesting -> {}'.format(url))
        content = resp.json()
        return content

    def _bind(self, collection_path, items):
        existing_paths = self.pod.list_dir(collection_path)
        existing_basenames = [path.lstrip('/') for path in existing_paths]
        new_basenames = []
        for item in items:
            item = self._get_single_job(item)
            item = self._parse_entry(item)
            path = os.path.join(collection_path, '{}.yaml'.format(item['id']))
            self.pod.write_yaml(path, item)
            self.pod.logger.info('Saving -> {}'.format(path))
            new_basenames.append(os.path.basename(path))
        basenames_to_delete = set(existing_basenames) - set(new_basenames)
        for basename in basenames_to_delete:
            # Skip deleting _blueprint, etc.
            if basename.startswith('_'):
                continue
            path = os.path.join(collection_path, basename)
            self.pod.delete_file(path)
            self.pod.logger.info('Deleting -> {}'.format(path))

    def run(self, *args, **kwargs):
        self.bind_jobs(
            self.config.api_key,
            self.config.jobs_collection)
