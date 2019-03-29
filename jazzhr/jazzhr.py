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
    # DEGREES_URL = 'https://api.greenhouse.io/v1/boards/{board_token}/education/degrees'
    # DEPARTMENTS_URL = 'https://api.greenhouse.io/v1/boards/{board_token}/departments'
    # DISCIPLINES_URL = 'https://api.greenhouse.io/v1/boards/{board_token}/education/disciplines'
    # JOBS_URL = 'https://api.greenhouse.io/v1/boards/{board_token}/jobs?content=true'
    # JOB_URL = 'https://api.greenhouse.io/v1/boards/{board_token}/jobs/{job_id}?questions=true'
    # SCHOOLS_URL = 'https://api.greenhouse.io/v1/boards/{board_token}/education/schools'

    class Config(messages.Message):
        api_key = messages.StringField(1)
        jobs_collection = messages.StringField(2)
        # departments_collection = messages.StringField(3)
        allowed_html_tags = messages.StringField(4, repeated=True)
        allowed_html_attributes = messages.MessageField(AttributeMessage, 5, repeated=True)
        # education_path = messages.StringField(6)
        # departments_blacklist = messages.StringField(7, repeated=True)

    def bind_jobs(self, api_key, collection_path):
        url = JazzhrPreprocessor.JOBS_URL.format(api_key=api_key)
        resp = requests.get(url)
	if resp.status_code != 200:
            raise Error('Error requesting -> {}'.format(url))
        content = resp.json()
        self._bind(collection_path, content)

    # def _download_schools(self, board_token):
    #     schools = {'items': []}
    #     total = 0
    #     items_so_far = 0
    #     page = 1
    #     has_run = False
    #     while not has_run or items_so_far < total:
    #         self.pod.logger.info('Downloading schools (page {})'.format(page))
    #         url = JazzhrPreprocessor.SCHOOLS_URL.format(board_token=board_token) + '?page={}'.format(page)
    #         resp = requests.get(url)
    #         if resp.status_code != 200:
    #             raise Error('Error requesting -> {}'.format(url))
    #         resp = resp.json()
    #         if not has_run:
    #             has_run = True
    #             total = resp.get('meta', {}).get('total_count', 0)
    #         schools['items'] += resp['items']
    #         items_so_far += len(resp['items'])
    #         page += 1
    #     return schools

    # def bind_education(self, board_token, education_path):
    #     schools = self._download_schools(board_token)
    #     url = JazzhrPreprocessor.DEGREES_URL.format(board_token=board_token)
    #     resp = requests.get(url)
	# if resp.status_code != 200:
    #         raise Error('Error requesting -> {}'.format(url))
    #     degrees = resp.json()
    #     url = JazzhrPreprocessor.DISCIPLINES_URL.format(board_token=board_token)
    #     resp = requests.get(url)
	# if resp.status_code != 200:
    #         raise Error('Error requesting -> {}'.format(url))
    #     disciplines = resp.json()
    #     item = {
    #         'degrees': degrees,
    #         'disciplines': disciplines,
    #         'schools': schools,
    #     }
    #     path = os.path.join(education_path)
    #     self.pod.write_yaml(path, item)
    #     self.pod.logger.info('Saving -> {}'.format(path))

    def _parse_entry(self, item):
        if item.get('title'):
            item['$title'] = item.pop('title')
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
        # departments_blacklist = self.config.departments_blacklist or []
        # departments_blacklist = [name.lower() for name in departments_blacklist]
        new_basenames = []
        for item in items:
            # Skip departments added to the blacklist.
            # department_names = [department.get('name', '').lower()
            #         for department in item.get('departments', [])]
            # skip = False
            # for name in department_names:
            #     if name in departments_blacklist:
            #        self.pod.logger.info('Skipping department -> {}'.format(name))
            #        skip = True
            # if skip:
            #     continue
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
