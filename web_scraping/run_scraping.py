from scraper import Scraper
from graph_generator import GraphGenerator


if __name__ == "__main__":
    urls = [
        # "https://sylabusy.agh.edu.pl/",
        "https://sd.agh.edu.pl/",
        "https://bg.agh.edu.pl/",
        "https://swfis.agh.edu.pl/",
        "https://www.sjo.agh.edu.pl/",
        "https://acmin.agh.edu.pl/",
        "https://spacetech.agh.edu.pl/pl/",
        "https://www.informatyka.agh.edu.pl/pl/",
        "https://wh.agh.edu.pl/",
        "https://www.wms.agh.edu.pl/",
        "https://www.fis.agh.edu.pl/",
        "https://weip.agh.edu.pl/",
        "https://www.zarz.agh.edu.pl/",
        "https://wnig.agh.edu.pl/",
        "https://wmn.agh.edu.pl/",
        "https://odlewnictwo.agh.edu.pl/",
        "https://www.ceramika.agh.edu.pl/",
        "https://www.wggios.agh.edu.pl/",
        "https://imir.agh.edu.pl/",
        "https://www.metal.agh.edu.pl/",
        "https://wilgz.agh.edu.pl/",
        "https://iet.agh.edu.pl/",
        "https://www.eaiib.agh.edu.pl/",
        "https://www.cok.agh.edu.pl/"
    ]
    # https://rekrutacja.agh.edu.pl/
    # https://akademik.agh.edu.pl/
    # https://dss.agh.edu.pl/
    # "https://www.miasteczko.agh.edu.pl"
    for url in urls:
        try:
            domain = url

            output_prefix = domain.split("/")[-2].replace(".", "_")

            crawler = GraphGenerator(
                allowed_domains=[domain],
                start_urls=[domain],
                max_pages=100
            )
            crawler.generate_graph()
            crawler.graph_to_json(f"{output_prefix}_graph.json")
            urls = crawler.get_nodes()

            scraper = Scraper(urls=urls)
            scraper.scrape()
            scraper.save_result_to_json(f"{output_prefix}_docs.json")
            # scraper.save_docs_as_md()
        except Exception as e:
            print(e)
