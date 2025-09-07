package com.mycompany.app;
import org.apache.iceberg.DeleteFile;
import org.apache.iceberg.FileMetadata;
import org.apache.iceberg.DeleteFiles;
import org.apache.iceberg.types.Types;
import org.apache.iceberg.DataFiles;
import org.apache.iceberg.data.GenericRecord;
import org.apache.iceberg.data.Record;
import org.apache.iceberg.data.GenericAppenderFactory;
import org.apache.hadoop.conf.Configuration;
import org.apache.iceberg.CatalogProperties;
import org.apache.iceberg.PartitionSpec;
import org.apache.iceberg.Schema;
import org.apache.iceberg.Table;
import org.apache.iceberg.catalog.TableIdentifier;
import org.apache.iceberg.catalog.Namespace;
import org.apache.iceberg.data.GenericAppenderFactory;
import org.apache.iceberg.data.GenericRecord;
import org.apache.iceberg.data.parquet.GenericParquetWriter;
import org.apache.iceberg.io.FileAppender;
import org.apache.iceberg.io.OutputFile;
import org.apache.iceberg.rest.RESTCatalog;
import org.apache.iceberg.types.Types;

import java.io.IOException;
import java.util.HashMap;
import java.util.Map;
import java.util.UUID;




public class IcebergTableReal implements AutoCloseable {

    private final RESTCatalog catalog;
    private final Table table;

    public IcebergTableReal() {
        Map<String, String> properties = new HashMap<>();
        properties.put(CatalogProperties.CATALOG_IMPL, "org.apache.iceberg.rest.RESTCatalog");
        properties.put(CatalogProperties.URI, "http://192.168.5.82:8181");
        properties.put(CatalogProperties.WAREHOUSE_LOCATION, "s3a://warehouse/wh");
        properties.put(CatalogProperties.FILE_IO_IMPL, "org.apache.iceberg.aws.s3.S3FileIO");
        properties.put("s3.endpoint", "http://192.168.5.82:9000");
        properties.put("s3.access-key-id", "admin");
        properties.put("s3.secret-access-key", "password");
        properties.put("s3.path-style-access", "true");

        catalog = new RESTCatalog();
        catalog.setConf(new Configuration());
        catalog.initialize("demo", properties);

        TableIdentifier tableIdentifier = TableIdentifier.of("my_namespace", "my_table");
        table = catalog.loadTable(tableIdentifier);
    }
    public void close() throws IOException {
    if (catalog != null) {
        catalog.close();
    }
   }
    // Append a row to the table
    public void addRow(long id, String dataValue) throws IOException {
        Schema schema = table.schema();
        PartitionSpec spec = table.spec();

        GenericRecord record = GenericRecord.create(schema);
        record.setField("id", id);
        record.setField("data", dataValue); 

        // Write one small Parquet file with the new row
        String filename = "data-" + UUID.randomUUID() + ".parquet";
        OutputFile out = table.io().newOutputFile(table.locationProvider().newDataLocation(filename));

        GenericAppenderFactory appenderFactory = new GenericAppenderFactory(schema);
        try (FileAppender<Record> writer =
         appenderFactory.newAppender(out, org.apache.iceberg.FileFormat.PARQUET)) {
         writer.add(record);
        }
        

        // Commit the new data file
        org.apache.iceberg.DataFile dataFile = org.apache.iceberg.DataFiles.builder(spec)
                .withPath(out.location())
                .withFileSizeInBytes(out.toInputFile().getLength())
                .withRecordCount(1)
                .build();

        table.newAppend()
             .appendFile(dataFile)
             .commit();

        System.out.println("Row added: " + record);
    }

   
   public void deleteByDataValue(String dataValue) throws IOException {
    Schema schema = table.schema();

    // Create a file for the equality delete
    String filename = "delete-" + UUID.randomUUID() + ".parquet";
    OutputFile out = table.io().newOutputFile(table.locationProvider().newDataLocation(filename));

    // Create a GenericRecord and set the 'data' field with the value to delete
    GenericRecord record = GenericRecord.create(schema);
    record.setField("data", dataValue);
      
    // Write the delete row into the delete file
    GenericAppenderFactory appenderFactory = new GenericAppenderFactory(schema);
    try (FileAppender<Record> writer =
                 appenderFactory.newAppender(out, org.apache.iceberg.FileFormat.PARQUET)) {
        writer.add(record);
    }

    // Build the delete file metadata, specifying "data" as the equality delete column
    DeleteFile deleteFile = FileMetadata.deleteFileBuilder(table.spec())
                .ofEqualityDeletes(schema.findField("data").fieldId())
                .withPath(out.location())
                .withFileSizeInBytes(out.toInputFile().getLength())
                .withRecordCount(1)
                .build();

    // Commit the equality delete
    table.newRowDelta()
                .addDeletes(deleteFile)
                .commit();

    System.out.println("All rows with data='" + dataValue + "' deleted");
}
   
   
    // Delete rows by equality delete
    public void deleteRow(long id) throws IOException {
    Schema schema = table.schema();

    // Create a file for the equality delete
    String filename = "delete-" + UUID.randomUUID() + ".parquet";
    OutputFile out = table.io().newOutputFile(table.locationProvider().newDataLocation(filename));

    GenericRecord record = GenericRecord.create(schema);
    record.setField("id", id);
     
     
    
      
    // Write the delete row into the delete file
    GenericAppenderFactory appenderFactory = new GenericAppenderFactory(schema);
    try (FileAppender<Record> writer =
                 appenderFactory.newAppender(out, org.apache.iceberg.FileFormat.PARQUET)) {
        writer.add(record);
    }

    // Build the delete file metadata
    DeleteFile deleteFile = FileMetadata.deleteFileBuilder(table.spec())
            .ofEqualityDeletes(schema.findField("id").fieldId())   // delete based on "id" column
            .withPath(out.location())
            .withFileSizeInBytes(out.toInputFile().getLength())
            .withRecordCount(1)
            .build();

    // Commit the equality delete
    table.newRowDelta()
            .addDeletes(deleteFile)
            .commit();

    System.out.println("Row with id=" + id + " deleted");
}
    
   
    public static void main(String[] args) throws Exception {
       IcebergTableReal iceberg = new IcebergTableReal();
        try {
        iceberg.addRow(101L, "Laptop");
        iceberg.addRow(102L, "Mouse");
        iceberg.deleteRow(101L);
        iceberg.deleteByDataValue("Laptop");
    } finally {
        iceberg.close();  // implement close() in your class
    }
    }
}

