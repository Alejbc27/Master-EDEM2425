FROM eclipse-temurin:21-jre
ENV MB_JETTY_PORT=8080
EXPOSE 8080
ADD https://storage.googleapis.com/cloud-sql-connectors/cloud-sql-proxy/v2.6.1/cloud-sql-proxy.linux.amd64 ./cloud_sql_proxy
ADD https://downloads.metabase.com/v0.53.8/metabase.jar ./metabase.jar

RUN chmod +x ./cloud_sql_proxy

CMD ["sh","-c","/cloud_sql_proxy --address 0.0.0.0 --port $MB_DB_PORT $MB_SQL_INSTANCE & exec java -jar /metabase.jar"]

