from scraper import Scraper
from urls_graph_generator import GraphGenerator


if __name__ == "__main__":
    domain = "https://rekrutacja.agh.edu.pl/"

    output_prefix = domain.split("/")[-1].replace(".", "_")

    crawler = GraphGenerator(
        allowed_domains=[domain],
        start_urls=[domain],
        max_pages=50
    )
    crawler.generate_graph()
    crawler.graph_to_json(f"{output_prefix}_graph.json")
    urls = crawler.get_nodes()

    scraper = Scraper(urls=urls)
    scraper.scrape()
    scraper.save_result_to_json(f"{output_prefix}_docs.json")
    scraper.save_docs_as_md()
