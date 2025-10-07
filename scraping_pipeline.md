
# Data scraping/processing pipeline overview

**1.** For the given domains (eg. agh.edu.pl, rekrutacja.agh.edu.pl) generate graph of connections
between pages under these domains (connections are buttons, links etc.)
   - This step is performed by `graph_generator.py`
   - Output of this process is the json file of following structure:
```json
{
  "source": "<SOURCE URL>",
  "target": "<TARGET URL>"
}
```
   - `source_url` is always a url available under the processed domain.


**2.** Scrape and process all nodes (urls) in the graphs.
    - Processing involves html parsing, text extraction, downloading files (.pdf, .docx etc) and filtering.
    - Nodes filtered out (eg. too short docs.) in the process are removed from the graphs.


**3.** Domains clustering. The result of the previous steps is a graph composed of multiple strongly connected components,
which are not strongly connected or even separated from each other. We want to cluster these components so that the ones
which are relatively small and highly correlated are merged. This step is presented in `web_graph_eda.ipynd` notebook.


**4.** Once we've grouped the data onto clusters we are indexing them to database. 
- Whole graph is saved in the separate collection in the database and contains information about 
nodes, its metadata (cluster id etc.) and connections between them.
- For each cluster separately, we are chunking the scraped data, generating the chunks embeddings, and saving them
in the vector store collection dedicated for this cluster. Such prepared collection can be queried by the retrieval agent.