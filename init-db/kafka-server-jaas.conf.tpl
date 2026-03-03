KafkaServer {
  org.apache.kafka.common.security.plain.PlainLoginModule required
  user_admin="__KAFKA_PASSWORD__"
  user_kafka="__KAFKA_PASSWORD__"
  user_readonly_admin="__KAFKA_PASSWORD__";
};

Client {
  org.apache.zookeeper.server.auth.DigestLoginModule required
  username="kafka"
  password="__KAFKA_PASSWORD__";
};

KafkaClient {
  org.apache.kafka.common.security.plain.PlainLoginModule required
  username="admin"
  password="__KAFKA_PASSWORD__";
};
