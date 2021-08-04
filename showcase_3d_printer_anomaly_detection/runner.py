import json
import os

import importlib_resources
import pandas as pd
from appdirs import AppDirs
from joblib import load
from kafka import KafkaProducer

from kafka_pc.KafkaPC import KafkaPC


def main():
    dirs = AppDirs("showcase-3d-printer-anomaly-detection")

    config_path = os.path.join(dirs.site_config_dir, "config.yaml")
    config_section = "General, anomaly_detection"

    kafka_pc = KafkaPC(config_path, config_section)
    producer = KafkaProducer(
        linger_ms=50,
        bootstrap_servers=[kafka_pc.config["KAFKA_BROKER_URL"]],
        value_serializer=lambda x: json.dumps(x).encode("utf-8"),
    )

    model_ref = importlib_resources.files("model") / "prediction_model.joblib"
    with importlib_resources.as_file(model_ref) as model_path:
        estimator = load(model_path)

    for msg in kafka_pc.consumer:
        data = json.loads(kafka_pc.decode_msg(msg))
        try:
            test_vector = pd.DataFrame(
                data[kafka_pc.config["JSON_QUERY"]],
                index=[0],
                columns=kafka_pc.config["DATA_COLUMNS"],
            )
            prediction = estimator.predict(
                test_vector.loc[
                    :,
                ]
            )
            if prediction == -1:
                print(data[kafka_pc.config["JSON_QUERY"]])
                try:
                    producer.send(kafka_pc.out_topic[0], data, partition=0)
                except Exception as e:
                    print(f"Error sending data to Kafka: {repr(e)}")
        except ValueError as ve:
            print(f"Could not parse input: {repr(ve)}")


if __name__ == "__main__":
    main()
