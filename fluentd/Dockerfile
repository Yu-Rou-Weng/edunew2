FROM fluent/fluentd:v1.14.5-debian-1.0
USER root
RUN gem uninstall -I elasticsearch && gem install elasticsearch -v 8.1.0
RUN ["gem", "install", "fluent-plugin-elasticsearch", "--no-document", "--version", "5.2.0"]
