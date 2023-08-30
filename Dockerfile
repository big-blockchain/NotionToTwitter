FROM python:3.10

# 创建 app 目录
WORKDIR /app

# 安装 app 依赖
COPY ./ /app

RUN apt update && apt install zlib1g && apt install zlib1g-dev

RUN pip install --upgrade pip
RUN pip install virtualenv
RUN virtualenv venv
RUN . venv/bin/activate

RUN pip install -r requirements.txt
RUN pip install -e .
# 打包 app 源码
# COPY . /app
RUN ls /app/secrets
CMD [ "python", "-u", "src/notionToTwitter.py", "--project", '$PROJECT' ]