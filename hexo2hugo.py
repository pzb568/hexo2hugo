#!/usr/bin/env python
# -*- coding: utf-8 -*-
import argparse
import datetime
import logging
import os
import re
import shutil
from dateutil import parser
import yaml
import pytoml as toml

# 默认配置
DEFAULT_LOGGING_LEVEL = logging.INFO
DEFAULT_TIMEZONE_OFFSET = datetime.timedelta(hours=8)
SUPPORTED_EXTENSIONS = ('.md', '.markdown', '.html')  # 支持的文件扩展名

class Logger:
    def __init__(self, name):
        log_format = 'Hexo2Hugo (%(name)s): [%(levelname)s] %(message)s'
        self.logger = logging.getLogger(name or __name__)
        self.logger.setLevel(DEFAULT_LOGGING_LEVEL)
        handler = logging.StreamHandler()
        handler.setFormatter(logging.Formatter(log_format))
        self.logger.addHandler(handler)

class Hexo2Hugo:
    def __init__(self, src, dest, remove_date, static_src, static_dest, verbose):
        self.root_path = os.path.expanduser(src)
        self.dest_path = os.path.expanduser(dest)
        self.static_src = os.path.expanduser(static_src) if static_src else None
        self.static_dest = os.path.expanduser(static_dest) if static_dest else None
        self.remove_date = remove_date
        self.logger = Logger("Hexo").logger
        if verbose:
            self.logger.setLevel(logging.DEBUG)

        # 确保目标目录存在
        self._ensure_directories()
        # 查找所有文件
        self._find_all_files()

    def _ensure_directories(self):
        """确保目标目录和静态资源目录存在"""
        try:
            os.makedirs(self.dest_path, exist_ok=True)
            self.logger.debug(f"Ensured directory exists: {self.dest_path}")
            if self.static_src and self.static_dest:
                os.makedirs(self.static_dest, exist_ok=True)
                self.logger.debug(f"Ensured static directory exists: {self.static_dest}")
        except Exception as e:
            self.logger.error(f"Failed to create directories: {e}")
            raise

    def _find_all_files(self):
        """查找源目录中的所有支持的文件"""
        self.files = []
        if not os.path.exists(self.root_path):
            self.logger.error(f"Source directory does not exist: {self.root_path}")
            raise FileNotFoundError(f"Source directory not found: {self.root_path}")
        
        for file in os.listdir(self.root_path):
            if file.lower().endswith(SUPPORTED_EXTENSIONS):
                self.files.append(file)
        self.logger.info(f"Total {len(self.files)} files found")

    def _remove_date(self, name):
        """从文件名中移除日期前缀"""
        new_name = re.sub(r'^\d{4}-\d{2}-\d{2}-(.*)', r'\1', name)
        return new_name if new_name else name

    def _extract_date_from_filename(self, filename):
        """从文件名提取日期"""
        match = re.match(r'^(\d{4}-\d{2}-\d{2})-.*$', filename)
        return match.group(1) if match else None

    def _process_files(self):
        """处理每个文件，提取元数据和内容"""
        for hexo_file in self.files:
            file_path = os.path.join(self.root_path, hexo_file)
            try:
                with open(file_path, 'r', encoding='utf-8') as fp:
                    meta_yaml = ''
                    body = ''
                    is_meta = False
                    is_first_line = True
                    is_in_pre = False

                    for line in fp:
                        if is_first_line:
                            is_first_line = False
                            if line.strip() == '---':
                                is_meta = True
                                continue

                        if is_meta:
                            if line.strip() == '---':
                                is_meta = False
                            else:
                                meta_yaml += line
                        else:
                            if hexo_file.lower().endswith('.html'):
                                if re.search(r'^<pre', line, re.IGNORECASE):
                                    is_in_pre = True
                                if re.search(r'^</pre', line, re.IGNORECASE):
                                    is_in_pre = False
                                if not is_in_pre and line.strip() and not re.search(r'<br */>$', line, re.IGNORECASE):
                                    body += line.rstrip() + "<br />\n"
                                else:
                                    body += line
                            else:
                                body += line

                    # 解析元数据
                    meta = yaml.safe_load(meta_yaml) or {}
                    self.logger.debug(f"Processing {hexo_file}, meta: {meta}, body length: {len(body)}")

                    # 处理日期
                    date_value = meta.get('date', '')
                    if isinstance(date_value, datetime.datetime):
                        no_tz_date = date_value
                    elif date_value:
                        no_tz_date = parser.parse(date_value)
                    else:
                        date_from_filename = self._extract_date_from_filename(hexo_file)
                        no_tz_date = parser.parse(date_from_filename) if date_from_filename else None
                    
                    if no_tz_date:
                        meta['date'] = no_tz_date.replace(tzinfo=datetime.timezone(DEFAULT_TIMEZONE_OFFSET)).isoformat()
                    else:
                        meta['date'] = ''

                    # 处理其他元数据
                    meta['description'] = meta.get('description', '')
                    if 'permalink' in meta:
                        meta['slug'] = meta['permalink']
                        del meta['permalink']
                    if 'layout' in meta:
                        del meta['layout']
                    if 'tags' in meta and isinstance(meta['tags'], str):
                        meta['tags'] = [tag.strip() for tag in meta['tags'].split(',')]
                    if 'categories' in meta and isinstance(meta['categories'], str):
                        meta['categories'] = [cat.strip() for cat in meta['categories'].split(',')]

                    # 转换为 TOML
                    meta_toml = toml.dumps(meta)
                    output_name = self._remove_date(hexo_file) if self.remove_date else hexo_file
                    yield {'name': output_name, 'meta': meta_toml, 'body': body}

            except Exception as e:
                self.logger.error(f"Failed to process {hexo_file}: {e}")
                continue

    def migrate_static(self):
        """迁移静态资源"""
        if not self.static_src or not self.static_dest:
            self.logger.info("Static migration skipped: static_src or static_dest not specified")
            return
        
        if not os.path.exists(self.static_src):
            self.logger.warning(f"Static source directory does not exist: {self.static_src}")
            return

        try:
            for item in os.listdir(self.static_src):
                src_path = os.path.join(self.static_src, item)
                dest_path = os.path.join(self.static_dest, item)
                if os.path.isdir(src_path):
                    shutil.copytree(src_path, dest_path, dirs_exist_ok=True)
                    self.logger.debug(f"Copied directory {src_path} to {dest_path}")
                else:
                    shutil.copy2(src_path, dest_path)
                    self.logger.debug(f"Copied file {src_path} to {dest_path}")
            self.logger.info(f"Static resources migrated from {self.static_src} to {self.static_dest}")
        except Exception as e:
            self.logger.error(f"Failed to migrate static resources: {e}")

    def go(self):
        """执行迁移"""
        # 处理文章
        for post in self._process_files():
            name = post['name']
            meta = post['meta']
            body = post['body']
            output_path = os.path.join(self.dest_path, name)
            try:
                with open(output_path, 'w', encoding='utf-8') as fp:
                    fp.write(f"+++\n{meta}+++\n\n{body}")
                    self.logger.info(f"Wrote to {output_path}")
            except Exception as e:
                self.logger.error(f"Failed to write {output_path}: {e}")

        # 迁移静态资源
        self.migrate_static()

def main():
    parser = argparse.ArgumentParser(description="Migrate Hexo posts to Hugo")
    parser.add_argument('--src', required=True, help='Hexo posts directory')
    parser.add_argument('--dest', required=True, help='Hugo content directory')
    parser.add_argument('--static-src', help='Hexo static resources directory (e.g., source/images)')
    parser.add_argument('--static-dest', help='Hugo static directory (e.g., static)')
    parser.add_argument('--remove-date-from-name', action='store_true', help='Remove date from file name')
    parser.add_argument('--verbose', action='store_true', help='Enable verbose logging')

    args = parser.parse_args()
    hexo = Hexo2Hugo(args.src, args.dest, args.remove_date_from_name, args.static_src, args.static_dest, args.verbose)
    hexo.go()

if __name__ == '__main__':
    main()