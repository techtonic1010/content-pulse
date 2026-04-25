package com.example.recommendation_service.recommendation;

import io.netty.channel.ChannelOption;
import io.netty.handler.timeout.ReadTimeoutHandler;
import java.util.Objects;
import java.util.concurrent.TimeUnit;
import org.springframework.boot.context.properties.EnableConfigurationProperties;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.http.client.reactive.ReactorClientHttpConnector;
import org.springframework.web.reactive.function.client.WebClient;
import reactor.netty.http.client.HttpClient;

@Configuration
@EnableConfigurationProperties(MlFastApiProperties.class)
public class WebClientConfig {

    @Bean
    public WebClient mlWebClient(MlFastApiProperties properties) {
        HttpClient httpClient = HttpClient.create()
            .option(ChannelOption.CONNECT_TIMEOUT_MILLIS, (int) Math.max(1, properties.getTimeoutMs()))
            .doOnConnected(connection ->
                connection.addHandlerLast(new ReadTimeoutHandler(Math.max(1, properties.getTimeoutMs()), TimeUnit.MILLISECONDS))
            );

        String baseUrl = Objects.requireNonNull(properties.getBaseUrl(), "ml.fastapi.base-url must not be null");
        ReactorClientHttpConnector connector = new ReactorClientHttpConnector(
            Objects.requireNonNull(httpClient, "httpClient must not be null")
        );

        return WebClient.builder()
            .baseUrl(baseUrl)
            .clientConnector(connector)
            .build();
    }
}
