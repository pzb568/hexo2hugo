一键将hexo转移至hugo


1.自动创建目录：
* 添加 _ensure_directories 方法，使用 os.makedirs(..., exist_ok=True) 确保 dest_path 和 static_dest 存在，解决 FileNotFoundError。
* 
2.中文和编码支持：
  
* 文件操作使用 encoding='utf-8'，确保中文文件名和内容正确处理。
* 
* 设置 PYTHONIOENCODING=utf-8（已通过 #!/usr/bin/env python 和 # -*- coding: utf-8 -*- 强化）。
* 
3.元数据处理：
  
支持字符串形式的 tags 和 categories 分割（如 tags: "tag1,tag2" → ["tag1", "tag2"]）。删除无关字段（如 layout），保留 description（即使为空）。规范化日期为 ISO 格式（带时区）。

4.静态资源迁移：

新增 --static-src 和 --static-dest 参数，支持迁移 Hexo 的 source/images/ 等到 Hugo 的 static/。使用 shutil.copytree 和 shutil.copy2 复制目录和文件，支持覆盖。

5.日志和错误处理：

默认日志级别改为 INFO，--verbose 启用 DEBUG。为文件处理和静态迁移添加异常捕获，防止单个文件错误中断脚本。提供详细日志（如文件路径、元数据、错误原因）。

6.文件扩展名支持：

支持 .md、.markdown 和 .html 文件，忽略非相关文件。HTML 文件的 <br /> 处理逻辑保留，Markdown 文件按原样输出。

7.代码结构：

模块化设计，分离日志、目录管理、文件处理和静态迁移。注释清晰，方便维护。

# 安装依赖Python库

```
pip install pyyaml python-dateutil pytoml

```
#生成hugo
```
hugo new site hugo
```

下载及一键转移

```
wget https://raw.githubusercontent.com/pzb568/hexo2hugo/refs/heads/master/hexo2hugo.py
chmod +x hexo2hugo.py
./hexo2hugo.py \
    --src=./hexoblog/source/_posts \
    --dest=./blog/content/posts \
    --static-src=./hexoblog/source \
    --static-dest=./blog/static \
    --remove-date-from-name \
    --verbose

```
参数说明：

--src：Hexo 文章目录（./hexo/source/_posts）。

--dest：Hugo 内容目录（./hugo/content/posts）。--static-src：Hexo 静态资源目录（./hexo/source，包含 images/ 等）。

--static-dest：Hugo 静态目录（./blog/static）。

--remove-date-from-name：移除文件名日期前缀。

--verbose：详细日志。
