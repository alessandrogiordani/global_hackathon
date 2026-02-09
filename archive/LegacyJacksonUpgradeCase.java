package com.ing.hackathon.mock;

import com.fasterxml.jackson.annotation.JsonInclude;
import com.fasterxml.jackson.annotation.JsonView;
import com.fasterxml.jackson.core.JsonGenerator;
import com.fasterxml.jackson.databind.*;
import com.fasterxml.jackson.databind.introspect.Annotated;
import com.fasterxml.jackson.databind.introspect.AnnotatedClass;
import com.fasterxml.jackson.databind.module.SimpleModule;

import java.io.IOException;
import java.util.List;

/**
 * Mock source file intentionally using older Jackson extension APIs
 * that are removed in newer versions.
 */
public class LegacyJacksonUpgradeCase {

    /* ===============================
       Custom AnnotationIntrospector
       =============================== */

    public static class LegacyAnnotationIntrospector extends AnnotationIntrospector {

        @Override
        public JsonInclude.Include findSerializationInclusion(
                Annotated a,
                JsonInclude.Include defValue) {
            return JsonInclude.Include.NON_NULL;
        }

        @Override
        public JsonInclude.Include findSerializationInclusionForContent(
                Annotated a,
                JsonInclude.Include defValue) {
            return defValue;
        }

        @Override
        public Class<?> findSerializationType(Annotated a) {
            return null;
        }

        @Override
        public Class<?> findSerializationKeyType(Annotated a, JavaType baseType) {
            return null;
        }

        @Override
        public Class<?> findSerializationContentType(Annotated a, JavaType baseType) {
            return null;
        }

        @Override
        public Class<?> findDeserializationType(Annotated a, JavaType baseType) {
            return null;
        }

        @Override
        public Class<?> findDeserializationKeyType(Annotated a, JavaType baseType) {
            return null;
        }

        @Override
        public Class<?> findDeserializationContentType(Annotated a, JavaType baseType) {
            return null;
        }

        @Override
        public Boolean findIgnoreUnknownProperties(AnnotatedClass ac) {
            return Boolean.TRUE;
        }

        @Override
        public String[] findPropertiesToIgnore(Annotated a) {
            return new String[] { "internalField" };
        }

        @Override
        public Object findFilterId(AnnotatedClass ac) {
            return "legacyFilter";
        }

        @Override
        public Version version() {
            return Version.unknownVersion();
        }
    }

    /* ===============================
       Custom Serializer
       =============================== */

    public static class LegacyOrderSerializer extends JsonSerializer<Order> {

        @Override
        public void serialize(Order value,
                              JsonGenerator gen,
                              SerializerProvider serializers) throws IOException {

            gen.writeStartObject();

            // Removed in newer Jackson versions
            Class<?> activeView = serializers.getSerializationView();

            gen.writeStringField("id", value.getId());
            gen.writeNumberField("total", value.getTotal());

            if (activeView != null) {
                gen.writeStringField("view", activeView.getName());
            }

            gen.writeEndObject();
        }
    }

    /* ===============================
       Facade Setup
       =============================== */

    public static ObjectMapper buildLegacyMapper() {
        ObjectMapper mapper = new ObjectMapper();

        mapper.setSerializationInclusion(JsonInclude.Include.NON_NULL);
        mapper.setAnnotationIntrospector(new LegacyAnnotationIntrospector());

        SimpleModule module = new SimpleModule("legacy-module");
        module.addSerializer(Order.class, new LegacyOrderSerializer());
        mapper.registerModule(module);

        return mapper;
    }

    /* ===============================
       Domain Model
       =============================== */

    public static class Order {

        public static class Views {
            public static class Public {}
            public static class Internal extends Public {}
        }

        private String id;

        @JsonView(Views.Public.class)
        private double total;

        @JsonView(Views.Internal.class)
        private List<String> items;

        public Order() {}

        public Order(String id, double total, List<String> items) {
            this.id = id;
            this.total = total;
            this.items = items;
        }

        public String getId() { return id; }
        public double getTotal() { return total; }
        public List<String> getItems() { return items; }

        public void setId(String id) { this.id = id; }
        public void setTotal(double total) { this.total = total; }
        public void setItems(List<String> items) { this.items = items; }
    }
}
