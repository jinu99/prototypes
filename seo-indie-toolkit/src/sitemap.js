const https = require('https');
const http = require('http');
const { parseStringPromise } = require('xml2js');

/**
 * URL에서 sitemap.xml을 가져와 URL 목록을 반환
 */
async function fetchSitemap(sitemapUrl) {
  const xml = await fetchUrl(sitemapUrl);
  const result = await parseStringPromise(xml);

  const urls = [];

  // 일반 sitemap
  if (result.urlset && result.urlset.url) {
    for (const entry of result.urlset.url) {
      urls.push(entry.loc[0]);
    }
  }

  // sitemap index
  if (result.sitemapindex && result.sitemapindex.sitemap) {
    for (const entry of result.sitemapindex.sitemap) {
      const childUrl = entry.loc[0];
      try {
        const childUrls = await fetchSitemap(childUrl);
        urls.push(...childUrls);
      } catch {
        // 하위 sitemap 실패 시 무시
      }
    }
  }

  return urls;
}

function fetchUrl(url) {
  return new Promise((resolve, reject) => {
    const client = url.startsWith('https') ? https : http;
    client.get(url, { headers: { 'User-Agent': 'SEO-Indie-Toolkit/1.0' } }, (res) => {
      if (res.statusCode >= 300 && res.statusCode < 400 && res.headers.location) {
        return fetchUrl(res.headers.location).then(resolve).catch(reject);
      }
      if (res.statusCode !== 200) {
        return reject(new Error(`HTTP ${res.statusCode} for ${url}`));
      }
      let data = '';
      res.on('data', chunk => data += chunk);
      res.on('end', () => resolve(data));
    }).on('error', reject);
  });
}

module.exports = { fetchSitemap };
