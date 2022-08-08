FROM python:3.10.6-bullseye

ADD create_certs.sh .
RUN apt-get update && apt-get install dos2unix -y \
    && dos2unix /create_certs.sh \
    && chmod +x /create_certs.sh \
    && /create_certs.sh /usr/local/share/ca-certificates/certs.crt \
    && update-ca-certificates

ENV NODE_EXTRA_CA_CERTS /usr/local/share/ca-certificates/certs.crt
ENV PATH /root/.local/bin:$PATH

# install zsh first
RUN apt-get update && apt-get install -y zsh wget \
    && sh -c "$(wget -O- https://github.com/deluan/zsh-in-docker/releases/download/v1.1.2/zsh-in-docker.sh)" -- \
    -p https://github.com/zsh-users/zsh-autosuggestions \
    -p https://github.com/zsh-users/zsh-completions \
    -p https://github.com/zsh-users/zsh-syntax-highlighting

ADD .p10k.zsh /root/.p10k.zsh
ADD .zshrc /root/.zshrc

SHELL [ "/bin/zsh", "-c" ]

RUN apt-get update && apt-get -y --no-install-recommends upgrade && apt-get install \
    git \
    gcc \
    nodejs \
    npm \
    ca-certificates \
    curl \
    build-essential \
    software-properties-common \
    -y \
    # poetry tools installation
    && curl -fsSL https://install.python-poetry.org | python3 - \
    && source ~/.zshrc \
    && python --version \
    && poetry --version \
    && source ~/.zshrc \
    && npm install -g jsdoc-to-markdown@5.0.3 \
    # install poetry plugin for oh my zsh
    && poetry completions zsh > $HOME/.oh-my-zsh/custom/plugins/poetry \
    && poetry config virtualenvs.in-project true \
    && apt-get autoclean && apt-get clean
