FROM ubuntu:bionic
RUN apt-get update -y
# Timezone configuration is required to avoid tzdata interuption while installing packages.
ENV TZ=Asia/Jakarta
RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone
RUN apt-get -y install software-properties-common build-essential python-dev python-pip git unzip
RUN add-apt-repository ppa:freecad-maintainers/freecad-daily
RUN apt-get update -y
RUN apt install -y freecad
COPY . .
RUN pip install -r requirements.txt
CMD [ "./kb_builder.py" ]
