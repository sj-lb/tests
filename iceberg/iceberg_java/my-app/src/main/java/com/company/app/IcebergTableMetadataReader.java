package com.mycompany.app;
import org.apache.iceberg.ManifestContent;
import com.fasterxml.jackson.databind.ObjectMapper;
import org.apache.iceberg.DataFile;
import org.apache.iceberg.ManifestFile;
import org.apache.iceberg.ManifestFiles;
import org.apache.iceberg.io.FileIO;
import org.apache.iceberg.io.CloseableIterable;
import com.fasterxml.jackson.databind.ObjectMapper;
import org.apache.hadoop.conf.Configuration;
import org.apache.iceberg.CatalogProperties;
import org.apache.iceberg.FileScanTask;
import org.apache.iceberg.ManifestFile;
import org.apache.iceberg.PartitionSpec;
import org.apache.iceberg.Schema;
import org.apache.iceberg.Snapshot;
import org.apache.iceberg.Table;
import org.apache.iceberg.TableScan;
import org.apache.iceberg.catalog.TableIdentifier;
import org.apache.iceberg.io.CloseableIterable;
import org.apache.iceberg.rest.RESTCatalog;
import org.apache.iceberg.types.Types;
import java.io.Closeable;
import java.io.IOException;
import java.util.HashMap;
import java.util.Map;
import java.util.HashSet;
import java.util.Set;
import java.util.List;
import org.apache.iceberg.DataFile;
import org.apache.iceberg.aws.s3.S3FileIO;
import org.apache.iceberg.ManifestFile;
import org.apache.iceberg.io.CloseableIterable;
import org.apache.iceberg.ManifestReader;
import org.apache.iceberg.ManifestFile;
import org.apache.iceberg.DataFile;
import org.apache.iceberg.io.FileIO;
import org.apache.iceberg.data.GenericRecord;
import org.apache.iceberg.ContentFile;


import org.apache.iceberg.ManifestFiles;
import org.apache.iceberg.DataFile;
/**
 * A Java class to connect to an Iceberg REST catalog, load an existing table,
 * and read its metadata, such as schema, partition specification, and manifest files.
 */
public class IcebergTableMetadataReader {

    public static void main(String[] args) {
        // Configuration for the REST Catalog, same as the creation class
        Map<String, String> properties = new HashMap<>();
        properties.put(CatalogProperties.CATALOG_IMPL, "org.apache.iceberg.rest.RESTCatalog");
        properties.put(CatalogProperties.URI, "http://192.168.5.82:8181");
        properties.put(CatalogProperties.WAREHOUSE_LOCATION, "s3a://warehouse/wh");
        properties.put(CatalogProperties.FILE_IO_IMPL, "org.apache.iceberg.aws.s3.S3FileIO");
        properties.put("s3.endpoint", "http://192.168.5.82:9000");
        properties.put("s3.access-key-id", "admin");
        properties.put("s3.secret-access-key", "password");
        properties.put("s3.path-style-access", "true");
        properties.put("s3.region", "us-east-1");

        RESTCatalog catalog = null;
        //try {
            S3FileIO s3FileIO = new S3FileIO();
            s3FileIO.initialize(Map.of(
    		"s3.endpoint", "http://192.168.5.82:9000",
    		"s3.access-key-id", "admin",
    		"s3.secret-access-key", "password",
    		"s3.path-style-access", "true",
    		"s3.region", "us-east-1"
		));
            // Initialize the REST catalog
            catalog = new RESTCatalog();
            Configuration conf = new Configuration();
            catalog.setConf(conf);
            catalog.initialize("demo", properties);

            // Define the table identifier for the table we want to read
            TableIdentifier tableIdentifier = TableIdentifier.of("my_namespace", "my_table");

            System.out.println("----------------------------------------");
            System.out.println("Loading table: " + tableIdentifier);

            // Load the existing Iceberg table from the catalog
            Table table = catalog.loadTable(tableIdentifier);

            // Print table metadata
            System.out.println("Successfully loaded table: " + table.name());
            System.out.println("Table location: " + table.location());

            // Print the schema
            Schema schema = table.schema();
            System.out.println("\nTable Schema:");
            for (Types.NestedField field : schema.asStruct().fields()) {
                System.out.println(String.format(
                        "  -> Field ID: %d, Name: %s, Type: %s, Is Required: %s, Doc: %s",
                        field.fieldId(),
                        field.name(),
                        field.type().toString(),
                        field.isRequired(),
                        field.doc() != null ? field.doc() : "N/A"
                ));
            }

            // Print the partition specification
            PartitionSpec spec = table.spec();
            System.out.println("\nPartition Specification:");
            if (spec.isUnpartitioned()) {
                System.out.println("  -> The table is unpartitioned.");
            } else {
                spec.fields().forEach(partitionField -> {
                    System.out.println(String.format(
                            "  -> Source Field: %s, Transform: %s, Partition Field Name: %s",
                            schema.findField(partitionField.sourceId()).name(),
                            partitionField.transform().toString(),
                            partitionField.name()
                    ));
                });
            }
            
            // Print snapshot information and manifest file details
         FileIO fileIO = table.io(); 
         if (table.currentSnapshot() != null) {
             System.out.println("\nLatest Snapshot:");
             Snapshot currentSnapshot = table.currentSnapshot();
             System.out.println("  -> Snapshot ID: " + currentSnapshot.snapshotId());
             System.out.println("  -> Timestamp (ms): " + currentSnapshot.timestampMillis());
             System.out.println("\nManifests in this Snapshot:");
              Set<String> manifestPaths = new HashSet<>();
              List<ManifestFile> manifests = currentSnapshot.allManifests(s3FileIO);
              ObjectMapper objectMapper = new ObjectMapper();
              for (ManifestFile manifest : manifests) {
                 System.out.println("Manifest file: " + manifest.path());
                 if (manifest.content() == ManifestContent.DATA){
                 try (ManifestReader<DataFile> reader = ManifestFiles.read(manifest, fileIO))  {
                      for (DataFile datafile : reader) {
                          System.out.println("  -> Data file_new: " + datafile.path());
                          Map<String, Object> jsonMap = new HashMap<>();
                          jsonMap.put("file_path", datafile.path());
                          jsonMap.put("file_format", datafile.format().name());
                          jsonMap.put("record_count", datafile.recordCount());
                          jsonMap.put("file_size_in_bytes", datafile.fileSizeInBytes());
                          String json = new com.fasterxml.jackson.databind.ObjectMapper()
                        .writerWithDefaultPrettyPrinter()
                        .writeValueAsString(jsonMap);
                System.out.println(json);

                          
                          
                          //String json = objectMapper
                          //             .writerWithDefaultPrettyPrinter()
                          //             .writeValueAsString(datafile);
                          //System.out.println("json" +json);
                          //System.out.println("Record count: " + dataFile.recordCount());	
                           
                      }
                 }
                 catch (Exception e){
                    System.err.println("An unexpected error occurred: " + e.getMessage());
                    e.printStackTrace(); // Prints the stack trace for debugging
                    System.exit(0);
                 }
                }
             }

         }//if              
     }//main     
}// class
