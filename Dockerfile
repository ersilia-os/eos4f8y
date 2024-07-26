FROM bentoml/model-server:0.11.0-py310
MAINTAINER ersilia

RUN wget https://github.com/ersilia-os/eos4f8y/blob/main/model/framework/mollib/virtual_libraries/environment_linux.yml
RUN conda config --set report_errors false
RUN conda env create -f environment_linux.yml --force
RUN rm environment_linux.yml
RUN pip install tqdm==4.66.2
RUN pip install rdkit==2023.3.1
RUN pip install pandas==1.3.5
RUN pip install joblib==1.3.2
RUN pip install scikit-learn==1.0.2
RUN pip install faiss-cpu==1.7.4
RUN pip install cdpkit==1.1.1
RUN conda install -c conda-forge xorg-libxrender xorg-libxtst

WORKDIR /repo
COPY . /repo
