FROM bentoml/model-server:0.11.0-py310
MAINTAINER ersilia

RUN wget https://github.com/ersilia-os/eos4f8y/blob/main/model/framework/mollib/virtual_libraries/environment_linux.yml
RUN conda config --set report_errors false
RUN conda env create -f environment_linux.yml --force
RUN rm environment_linux.yml

WORKDIR /repo
COPY . /repo
