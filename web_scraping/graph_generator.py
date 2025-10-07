import json
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin
import pandas as pd
import networkx as nx
from urllib.parse import urlparse
import plotly.graph_objects as go
from tqdm import tqdm
import time
import random


class GraphGenerator:
    """
    A web crawler that generates a directed graph of web pages and their links.

    Starting from a list of seed URLs, it crawls within specified allowed domains,
    builds a NetworkX directed graph (DiGraph) of link relationships, and
    provides utilities for exporting and analyzing the graph.

    Attributes
    ----------
    allowed_domains : set
        The set of domains allowed for recursive crawling.
    start_urls : set
        The set of initial seed URLs to start crawling from.
    max_pages : int
        Maximum number of pages to crawl per seed URL.
    visited_urls : set
        Global set of already visited URLs across all crawls.
    G : nx.DiGraph
        The directed graph structure storing nodes (URLs) and edges (links).
    """

    def __init__(self, start_urls, allowed_domains, max_pages=10):
        """
        Initialize the GraphGenerator.

        Parameters
        ----------
        start_urls : list[str] or set[str]
            Seed URLs to start crawling from.
        allowed_domains : list[str] or set[str]
            Domains that are allowed for recursive crawling.
        max_pages : int, optional
            Maximum number of pages to crawl per seed, by default 10.
        """
        self.allowed_domains = set(allowed_domains)
        self.start_urls = set(start_urls)
        self.max_pages = max_pages
        self.visited_urls = set()
        self.G = nx.DiGraph()

    def generate_graph(self):
        """
        Generate a graph by crawling from all start URLs.

        Returns
        -------
        nx.DiGraph
            The directed graph of crawled pages and links.
        """
        for start_url in self.start_urls:
            self.crawl(start_url, self.max_pages)
        return self.G

    def crawl(self, start_url, max_pages, delay=1):
        """
        Crawl the web starting from a given URL, following only links
        within allowed domains. External nodes are added to the graph
        but not crawled further.

        Parameters
        ----------
        start_url : str
            The URL to start crawling from.
        max_pages : int
            Maximum number of pages to crawl.
        delay : int or float, optional
            Base delay between requests in seconds, by default 1.
        """
        start_domain = urlparse(start_url).netloc
        self.allowed_domains.add(start_domain)

        queue = [start_url]
        pbar = tqdm(total=max_pages, desc="Crawling")
        visited = []

        while queue and len(visited) < max_pages:
            current_url = queue.pop(0)

            if current_url in visited or current_url in self.visited_urls:
                continue

            extensions_to_filter = [".jpg"]
            for extensions in extensions_to_filter:
                if current_url.endswith(extensions):
                    continue

            visited.append(current_url)
            pbar.update(1)

            try:
                links_df = self.extract_links_from_url(current_url)

                if links_df is not None and not links_df.empty:
                    for link in links_df['url']:
                        self.G.add_edge(current_url, link)

                        if self.is_allowed_domain(link):
                            if link not in visited and link not in self.visited_urls:
                                queue.append(link)
                        else:
                            if link not in self.G:
                                self.G.add_node(link)

                if current_url not in self.G:
                    self.G.add_node(current_url)

                time.sleep(delay + random.uniform(0, 0.5))

            except Exception as e:
                print(f"Error crawling {current_url}: {e}")

        for url in visited:
            self.visited_urls.add(url)

        pbar.close()

    def is_allowed_domain(self, url):
        """
        Check whether a given URL belongs to one of the allowed domains.

        Parameters
        ----------
        url : str
            The URL to check.

        Returns
        -------
        bool
            True if the URL is within allowed domains, False otherwise.
        """
        try:
            parsed_url = urlparse(url)
            domain = parsed_url.netloc
            return domain in self.allowed_domains or any(
                domain.endswith('.' + d) for d in self.allowed_domains
            )
        except Exception:
            return False

    def extract_links_from_url(self, url):
        """
        Extract all hyperlinks from a given web page.

        Parameters
        ----------
        url : str
            The URL of the page to extract links from.

        Returns
        -------
        pd.DataFrame
            A DataFrame with columns:
            - 'url': absolute link URLs
            - 'file_extension': file extension of the linked resource
        """
        try:
            headers = {
                'User-Agent': (
                    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
                    'AppleWebKit/537.36 (KHTML, like Gecko) '
                    'Chrome/91.0.4472.124 Safari/537.36'
                )
            }
            response = requests.get(url, headers=headers, timeout=10)
            response.raise_for_status()
        except requests.exceptions.RequestException as e:
            print(f"Error fetching the URL: {e}")
            return pd.DataFrame(columns=['link_text', 'url', 'link_type', 'file_extension'])

        soup = BeautifulSoup(response.text, 'html.parser')
        base_url = url

        link_urls = []
        file_extensions = []

        for a_tag in soup.find_all('a', href=True):
            href = a_tag.get('href')
            if not href or href.startswith(('javascript:', '#')):
                continue

            absolute_url = urljoin(base_url, href)
            parsed_url = urlparse(absolute_url)
            path = parsed_url.path.lower()
            file_extension = path.split('.')[-1] if '.' in path else ''

            link_urls.append(absolute_url)
            file_extensions.append(file_extension if file_extension else "None")

        df = pd.DataFrame({
            'url': link_urls,
            'file_extension': file_extensions
        })

        df = df.drop_duplicates(subset=['url'])
        return df

    def graph_to_json(self, output_file):
        """
        Export the graph to a JSON file.

        Parameters
        ----------
        output_file : str
            Path to the output JSON file.
        """
        nodes = [{"url": node} for node in self.G.nodes]
        edges = [{"source": u, "target": v} for u, v in self.G.edges]

        with open(output_file, "w") as f:
            json.dump({
                "nodes": nodes,
                "edges": edges
            }, f, indent=4)

    def get_nodes(self):
        """
        Return all nodes in the graph.

        Returns
        -------
        list[str]
            List of URLs present in the graph.
        """
        return list(self.G.nodes())