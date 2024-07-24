FROM bentoml/model-server:0.11.0-py310
MAINTAINER ersilia

RUN wget https://github.com/miquelduranfrigola/eos4f8y/blob/main/model/framework/mollib/virtual_libraries/environment_linux.yml
RUN conda env create -f environment_linux.yml
RUN rm environment_linux.yml

WORKDIR /repo
COPY . /repo
