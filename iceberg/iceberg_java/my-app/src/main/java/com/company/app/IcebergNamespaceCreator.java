package com.mycompany.app;
import org.apache.hadoop.conf.Configuration;
import org.apache.iceberg.CatalogProperties;
import org.apache.iceberg.rest.RESTCatalog;
import org.apache.iceberg.catalog.Namespace;
import org.apache.iceberg.catalog.TableIdentifier;
import org.apache.iceberg.catalog.Namespace; // Import the correct interface
import org.apache.iceberg.aws.AwsProperties;
import java.util.HashMap;
import java.util.Map;
import java.io.Closeable;
import java.io.IOException;

public class IcebergNamespaceCreator {

    public static void main(String[] args) {
      

        Map<String, String> properties = new HashMap<>();
        properties.put(CatalogProperties.CATALOG_IMPL, "org.apache.iceberg.rest.RESTCatalog");
        //properties.put(CatalogProperties.URI, "http://rest:8181");
	properties.put(CatalogProperties.URI, "http://192.168.5.82:8181");
        properties.put(CatalogProperties.WAREHOUSE_LOCATION, "s3a://warehouse/wh");
        properties.put(CatalogProperties.FILE_IO_IMPL, "org.apache.iceberg.aws.s3.S3FileIO");	   
        properties.put("s3.endpoint", "http://192.168.5.82:9000");    
        properties.put("s3.access-key-id", "admin");
        properties.put("s3.secret-access-key", "password");
        properties.put("s3.path-style-access", "true");







        // Use the NamespaceCatalog interface for namespace-related operations
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
        //try {
            if (!catalog.namespaceExists(namespace)) {
                catalog.createNamespace(namespace);
                System.out.println("----------------------------------------");
                System.out.println("Successfully created namespace: " + namespace);
                System.out.println("----------------------------------------");
            } else {
                System.out.println("Namespace " + namespace + " already exists. Skipping creation.");
            }
        } catch (Exception e) {
            System.err.println("Failed to create the Iceberg namespace.");
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


