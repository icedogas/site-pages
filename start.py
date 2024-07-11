import requests
from bs4 import BeautifulSoup
from urllib.parse import urlparse, urljoin
import time
import pandas as pd


class SiteCrawler:
    def __init__(self, start_url):
        self.start_url = start_url
        self.visited_links = set()
        self.domain = urlparse(start_url).netloc

    def is_internal_link(self, link):
        return urlparse(link).netloc == self.domain or urlparse(link).netloc == ''

    def get_absolute_url(self, link):
        return urljoin(self.start_url, link)

    def fetch_links(self, url):
        internal_links = set()
        headers = {
            "User-Agent": "Mozilla/5.0 (compatible; Googlebot/2.1; +http://www.google.com/bot.html)"}

        # Дополнительные расширения можно добавить по необходимости
        image_extensions = ['.jpg', '.jpeg', '.png', '.gif', '.svg', '.webp']
        try:
            response = requests.get(url, headers=headers, timeout=10)
            content_type = response.headers.get('Content-Type', '')

            # Определение типа контента для выбора парсера
            if 'xml' in content_type:
                features = "xml"
            else:
                features = "html.parser"

            soup = BeautifulSoup(response.content, features=features)

            # Разбор HTML и XML контента
            if features == "html.parser":
                tags = soup.find_all('a', href=True)
            else:  # Для XML-документов, например RSS-фидов
                tags = soup.find_all('link')

            for link in tags:
                href = link['href'] if features == "html.parser" else link.text

                if href.startswith('javascript:') or href == '#' or any(href.endswith(ext) for ext in image_extensions):
                    continue

                processed_href = urlparse(href)._replace(fragment='').geturl()
                if self.is_internal_link(processed_href):
                    full_url = self.get_absolute_url(processed_href)
                    internal_links.add(full_url)
        except Exception as e:
            print(f"Ошибка при обработке {url}: {e}")
        return internal_links

    def crawl(self, url):
        if url in self.visited_links:
            return

        print(f"Обработка: {url}")
        self.visited_links.add(url)
        internal_links = self.fetch_links(url)

        for link in internal_links:
            if link not in self.visited_links:
                self.crawl(link)
                time.sleep(1)  # Рекомендуется задержка между запросами

    def fetch_sitemap_links(self, sitemap_url):
        sitemap_links = set()
        headers = {
            "User-Agent": "Mozilla/5.0 (compatible; Googlebot/2.1; +http://www.google.com/bot.html)"}

        try:
            response = requests.get(sitemap_url, headers=headers, timeout=10)
            if response.status_code == 200:
                content_type = response.headers.get('Content-Type', '')

                # Проверяем, является ли контент XML
                if 'xml' in content_type:
                    soup = BeautifulSoup(response.content, features="xml")
                    loc_tags = soup.find_all("loc")

                    for loc in loc_tags:
                        loc_url = loc.text
                        if loc_url.endswith('.xml') and loc_url != sitemap_url:
                            sitemap_links = sitemap_links.union(self.fetch_sitemap_links(
                                loc_url))  # Рекурсивный вызов для вложенных Sitemap
                        else:
                            sitemap_links.add(loc_url)
        except Exception as e:
            print(f"Ошибка при обработке Sitemap {sitemap_url}: {e}")

        return sitemap_links


def analyze_sites(file_name):
    results = []
    urls = read_urls_from_file(file_name)

    for url in urls:
        crawler = SiteCrawler(url)
        # Подсчет страниц, найденных при обходе сайта
        crawler.crawl(url)
        internal_links_count = len(crawler.visited_links)

        # Подсчет страниц в sitemap.xml
        sitemap_links_count = len(crawler.fetch_sitemap_links(
            url.rstrip('/') + '/sitemap.xml'))

        results.append((url, internal_links_count, sitemap_links_count))

    df = pd.DataFrame(results, columns=[
                      'Сайт', 'Уникальных внутренних ссылок', 'Страниц в sitemap.xml'])
    df.to_csv('results.csv', sep=';',
              index=False, encoding='utf-8-sig')
    print("Обработка завершена. Результаты сохранены в 'results.csv'.")


def read_urls_from_file(file_name):
    with open(file_name, 'r') as file:
        return [line.strip() for line in file]


if __name__ == "__main__":
    analyze_sites('urls.txt')
