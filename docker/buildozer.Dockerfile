# 自建 buildozer 镜像:固定基础镜像和 python 版本,不再依赖
# ghcr.io/kivy/buildozer:latest (会随上游更新漂移,例如最近升级到了
# ubuntu:26.04 / python 3.14,导致 hostpython3 与 buildozer.spec 里
# requirements 钉的 python3==3.11.9 不一致而构建失败)
#
# 构建:
#   docker build -t mycgc-buildozer -f docker/buildozer.Dockerfile .
# 运行(和 kivy/buildozer 官方镜像的用法保持一致,挂载项目目录 + 持久化 SDK/NDK 缓存):
#   docker run --rm \
#     -v "$PWD":/root/hostcwd \
#     -v "$PWD/.buildozer_cache":/root/.buildozer \
#     mycgc-buildozer android debug

FROM python:3.11-bookworm

ENV USER="user"
ENV HOME_DIR="/home/${USER}"
ENV WORK_DIR="${HOME_DIR}/hostcwd" \
    SRC_DIR="${HOME_DIR}/src" \
    PATH="${HOME_DIR}/.local/bin:${PATH}"

# locale(和官方镜像保持一致,避免某些工具因为 locale 缺失报错)
RUN apt-get update -qq > /dev/null \
    && DEBIAN_FRONTEND=noninteractive apt-get install -qq --yes --no-install-recommends \
       locales \
    && locale-gen en_US.UTF-8
ENV LANG="en_US.UTF-8" \
    LANGUAGE="en_US.UTF-8" \
    LC_ALL="en_US.UTF-8"

# 编译大多数 p4a recipe 需要的系统依赖(照抄官方 Dockerfile 的清单,
# 去掉了 python3-pip/python3-setuptools/python3-venv,因为 python:3.11
# 基础镜像已经自带这些)
RUN apt-get update -qq > /dev/null \
    && DEBIAN_FRONTEND=noninteractive apt-get install -qq --yes --no-install-recommends \
       autoconf \
       automake \
       build-essential \
       ccache \
       cmake \
       gettext \
       git \
       libffi-dev \
       libltdl-dev \
       libssl-dev \
       libtool \
       openjdk-17-jdk \
       patch \
       pkg-config \
       sudo \
       unzip \
       zip \
       zlib1g-dev \
    && rm -rf /var/lib/apt/lists/*

RUN useradd --create-home --shell /bin/bash ${USER} \
    && echo "${USER} ALL=(ALL) NOPASSWD:ALL" >> /etc/sudoers \
    && mkdir -p ${WORK_DIR} \
    && chown -R ${USER}:${USER} ${HOME_DIR}

USER ${USER}
WORKDIR ${WORK_DIR}

RUN python3 -m venv ${HOME_DIR}/.venv
ENV VIRTUAL_ENV="${HOME_DIR}/.venv"
ENV PATH="${VIRTUAL_ENV}/bin:${PATH}"

RUN pip install --upgrade "Cython<3.0" wheel pip buildozer

ENTRYPOINT ["buildozer"]
