package com.mycompany.app;
import org.apache.hadoop.conf.Configuration;
import org.apache.iceberg.CatalogProperties;
import org.apache.iceberg.rest.RESTCatalog;
import org.apache.iceberg.catalog.Namespace;
import org.apache.iceberg.catalog.TableIdentifier;
import org.apache.iceberg.catalog.Namespace; // Import the correct interface
import org.apache.iceberg.aws.AwsProperties;
import org.apache.iceberg.Table;
import org.apache.iceberg.Schema;
import org.apache.iceberg.types.Types;
import org.apache.iceberg.PartitionSpec;
import java.util.HashMap;
import java.util.Map;
import java.io.Closeable;
import java.io.IOException;

public class IcebergTableCreator {

    public static void main(String[] args) {
        System.out.println("Strating IcebergTableCreator "); 
        // Configuration for the REST Catalog (running in the iceberg-rest container)
        Map<String, String> properties = new HashMap<>();
        properties.put(CatalogProperties.CATALOG_IMPL, "org.apache.iceberg.rest.RESTCatalog");
       
	properties.put(CatalogProperties.URI, "http://192.168.5.82:8181");
        properties.put(CatalogProperties.WAREHOUSE_LOCATION, "s3a://warehouse/wh");
        properties.put(CatalogProperties.FILE_IO_IMPL, "org.apache.iceberg.aws.s3.S3FileIO");	   
        properties.put("s3.endpoint", "http://192.168.5.82:9000");    
        properties.put("s3.access-key-id", "admin");
        properties.put("s3.secret-access-key", "password");
        properties.put("s3.path-style-access", "true");
        // The REST catalog does not support creating a session, so we use it directly
       RESTCatalog catalog=null;
       try {  
        catalog = new RESTCatalog(); // This line would involve initialization details
        Configuration conf = new Configuration();
	catalog.setConf(conf);
        catalog.initialize("demo", properties);		
	System.out.println(catalog);
	if(catalog == null)
	   System.out.println(" catalog  NULL");
        else
	   System.out.println(" catalog   not NULL");	
        Namespace namespace = Namespace.of("my_namespace");
        if(namespace == null)
		System.out.println(" namespace NULL");
	else
             System.out.println(" namespace not NULL");		

        // Define the table identifier (namespace and table name)
        TableIdentifier tableIdentifier = TableIdentifier.of("my_namespace", "my_table");

      
            // Define a simple schema for the new table
            Schema schema = new Schema(
                Types.NestedField.required(1, "id", Types.LongType.get(), "Unique ID"),
                Types.NestedField.optional(2, "data", Types.StringType.get())
            );

            // Define a partition specification for the new table (unpartitioned in this case)
            PartitionSpec spec = PartitionSpec.unpartitioned();

            // Create the Iceberg table
            Table table = catalog.createTable(tableIdentifier, schema, spec);
            
            System.out.println("----------------------------------------");
            System.out.println("Successfully created table: " + tableIdentifier);
            System.out.println("Table location: " + table.location());
            System.out.println("----------------------------------------");

        } catch (Exception e) {
            System.err.println("Failed to create the Iceberg table.");
            e.printStackTrace();
        } finally {
            if (catalog instanceof Closeable) {
                try {
                    ((Closeable) catalog).close();
                } catch (IOException e) {
                    e.printStackTrace();
                }
            }
        }
    }
}

