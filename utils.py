import os
import requests
import feedparser
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
from openai import OpenAI
import json
import re

# ===========================
# 资讯抓取模块 (News Aggregator)
# ===========================

class NewsFetcher:
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        })

    def fetch_hacker_news_ai(self, limit=10, domains=None, time_span="Last 24 Hours (Fresh)"):
        """通过 Algolia API 获取 Hacker News 上最新的 AI 相关讨论"""
        print(f"正在获取 Hacker News... Domains: {domains}, TimeSpan: {time_span}")
        
        # 1. 确定时间窗口和排序策略
        now = datetime.now()
        timestamp_threshold = 0
        use_search_by_date = True # 默认按时间倒序(求新)，如果是 Trending 则用 search

        if "24 Hours" in time_span:
            timestamp_threshold = int((now - timedelta(hours=24)).timestamp())
            use_search_by_date = True
        elif "3 Days" in time_span:
            timestamp_threshold = int((now - timedelta(days=3)).timestamp())
            use_search_by_date = False # 使用相关性/热度排序，但在时间范围内
        elif "7 Days" in time_span:
            timestamp_threshold = int((now - timedelta(days=7)).timestamp())
            use_search_by_date = False
            
        # 2. 构建查询关键词 (Query Injection)
        base_keywords = ["LLM", "AI", "GPT", "Transformer"]
        domain_keywords = []

        if domains:
            if "Robotics" in domains:
                domain_keywords.extend(["Robotics", "Robot", "Hardware", "Actuator"])
            if "Finance/Quant" in domains:
                domain_keywords.extend(["Quant", "Trading", "Finance", "Algorithmic"])
            if "Programming/SE" in domains:
                domain_keywords.extend(["Copilot", "IDE", "Rust", "Python", "Engineering", "Developer"])
            if "Computer Vision" in domains:
                 domain_keywords.extend(["Vision", "Image", "Video", "Diffusion", "YOLO"])
        
        # 组合查询: (Base OR Base...) AND (Domain OR Domain...)
        # 如果没有选特定领域，默认还是只搜 Base
        query_str = " OR ".join(base_keywords)
        if domain_keywords:
            domain_query = " OR ".join(domain_keywords)
            query_str = f"({query_str}) AND ({domain_query})"

        try:
            # 3. 选择接口
            # search_by_date: 按时间倒序，适合 "Fresh"
            # search: 按相关性(通常也关联热度)排序，适合 "Trending"
            endpoint = "search_by_date" if use_search_by_date else "search"
            url = f"https://hn.algolia.com/api/v1/{endpoint}"
            
            params = {
                "query": query_str,
                "tags": "story",
                "hitsPerPage": limit,
                "numericFilters": f"created_at_i>{timestamp_threshold}"
            }
            
            response = self.session.get(url, params=params, timeout=10)
            data = response.json()
            hits = data.get('hits', [])

            # Fallback 1: Relax time constraint
            if not hits:
                print(f"Warning: No results in last {time_span}. Fetching absolute latest items instead.")
                params.pop("numericFilters", None)
                response = self.session.get(url, params=params, timeout=10)
                data = response.json()
                hits = data.get('hits', [])

            # Fallback 2: Relax domain constraint (Broad AI search)
            if not hits and domains:
                print(f"Warning: No results for domains {domains}. Fetching generic AI news.")
                params["query"] = " OR ".join(base_keywords) # Reset to base query
                response = self.session.get(url, params=params, timeout=10)
                data = response.json()
                hits = data.get('hits', [])
            
            results = []
            min_points = 5
            if "Trending" in time_span or "Best" in time_span:
                min_points = 50 # 提高门槛
                
            for hit in hits:
                points = hit.get('points', 0)
                if points < min_points:
                    continue
                    
                results.append({
                    "source": "Hacker News",
                    "title": hit.get('title'),
                    "url": hit.get('url') or f"https://news.ycombinator.com/item?id={hit.get('objectID')}",
                    "summary": f"Points: {points} | Comments: {hit.get('num_comments')}",
                    "raw_data": hit
                })
            
            # 如果是 Trending 模式，虽然 API 可能是按相关性排的，我们手动按 Points 再排一次以防万一
            if not use_search_by_date:
                results.sort(key=lambda x: x['raw_data'].get('points', 0), reverse=True)
                
            return results
        except Exception as e:
            print(f"Error fetching Hacker News: {e}")
            return []

    def fetch_arxiv_papers(self, limit=5, domains=None, time_span="Last 24 Hours (Fresh)"):
        """获取最新的 CS.AI 论文"""
        print(f"正在获取 arXiv 论文... Domains: {domains}")
        
        # 1. 映射 Categories
        # 基础分类
        categories = ["cs.AI", "cs.CL"] # AI, Computation and Language
        
        if domains:
            if "Robotics" in domains:
                categories.append("cs.RO")
            if "Finance/Quant" in domains:
                categories.extend(["q-fin.TR", "q-fin.CP"]) # Trading, Computational Finance
            if "Programming/SE" in domains:
                categories.extend(["cs.SE", "cs.PL"]) # Software Engineering, Programming Languages
            if "Computer Vision" in domains:
                categories.append("cs.CV")
        
        # Logically join them with OR
        cat_query = "+OR+".join([f"cat:{c}" for c in categories])
        
        try:
            # 2. 调用 API
            # arXiv API 不太好做复杂的按热度排序，通常只有 submittedDate, lastUpdatedDate, relevance
            # 我们保持按 submittedDate (Top Fetch)
            
            # 如果是 Trending (TimeSpan > 24h)，我们稍微增加一点 limit，以便获取更多样本用于后续(虽然这里没做二次筛选)
            # 或者，如果 API 支持，我们可以不做太多改变，因为 arXiv 主要看的是新发论文。
            # "Trending" for arXiv is hard without citation counts. We stick to latest.
            
            url = f"http://export.arxiv.org/api/query?search_query={cat_query}&sortBy=submittedDate&sortOrder=descending&start=0&max_results={limit}"
            response = self.session.get(url, timeout=30)
            feed = feedparser.parse(response.content)
            
            results = []
            for entry in feed.entries:
                results.append({
                    "source": "arXiv",
                    "title": entry.title.replace('\n', ' '),
                    "url": entry.link,
                    "summary": entry.summary[:300] + "...",
                    "published": entry.published
                })
            return results
        except Exception as e:
            print(f"Error fetching arXiv: {e}")
            return []
            
    def fetch_huggingface_daily(self, domains=None, time_span="Last 24 Hours (Fresh)"):
        """获取 Hugging Face Papers"""
        print("正在获取 Hugging Face Papers...")
        try:
            # HF 页面默认是 Daily。
            # 只有简单的 date 参数或者页码，很难做 keyword 搜索。
            # 策略：抓取回结果后，在 Python 层面做简单的 Title/Summary 关键词过滤。
            
            url = "https://huggingface.co/papers"
            response = self.session.get(url, timeout=10)
            if response.status_code != 200:
                print(f"HF Status Code: {response.status_code}")
                return []
                
            soup = BeautifulSoup(response.text, 'html.parser')
            # 提高抓取数量，以便后续过滤
            fetch_limit = 20 if domains else 5
            articles = soup.find_all('article', limit=fetch_limit)
            
            domain_keywords = []
            if domains:
                if "General LLM" in domains or "通用 LLM" in domains:
                    domain_keywords.extend(["llm", "language model", "gpt", "transformer", "generative", "agent", "reasoning"])
                if "Robotics" in domains:
                    domain_keywords.extend(["robot", "hardware", "manipulation", "locomotion"])
                if "Finance/Quant" in domains:
                    domain_keywords.extend(["financial", "trading", "market", "stock", "quant"])
                if "Programming/SE" in domains:
                    domain_keywords.extend(["code", "program", "software", "repository", "bug"])
                if "Computer Vision" in domains:
                    domain_keywords.extend(["vision", "image", "video", "detection", "segmentation", "diffusion"])
            
            results = []
            for art in articles:
                h3 = art.find('h3')
                if h3:
                    a_tag = h3.find('a')
                    if a_tag:
                        # 处理相对链接
                        href = a_tag.get('href', '')
                        if href.startswith('/'):
                            link = "https://huggingface.co" + href
                        else:
                            link = href
                            
                        title = a_tag.get_text(strip=True)
                        
                        # Client-side Domain Filtering
                        if domain_keywords:
                            title_lower = title.lower()
                            # 只要标题包含任一关键词即可
                            if not any(k in title_lower for k in domain_keywords):
                                continue # Skip this item
                        
                        results.append({
                            "source": "Hugging Face Daily",
                            "title": title,
                            "url": link,
                            "summary": "Hugging Face Daily 热门论文"
                        })
            
            # 如果过滤后太少，可能用户体验不好，但保证了垂直度
            return results[:10] # 限制最终返回数量
        except Exception as e:
            print(f"Error fetching Hugging Face: {e}")
            return []

    def fetch_tech_news_rss(self, limit=15, domains=None, time_span="Last 24 Hours (Fresh)"):
        """获取主流科技媒体 RSS (多个来源)"""
        print(f"正在获取科技媒体 RSS... Domains: {domains}")
        
        # 扩展 RSS 源列表
        rss_urls = [
            # TechCrunch AI
            ("https://techcrunch.com/category/artificial-intelligence/feed/", "TechCrunch"),
            # The Verge AI
            ("https://www.theverge.com/rss/artificial-intelligence/index.xml", "The Verge"),
            # VentureBeat AI
            ("https://venturebeat.com/category/ai/feed/", "VentureBeat"),
            # Wired AI
            ("https://www.wired.com/feed/tag/ai/latest/rss", "Wired"),
            # Ars Technica AI
            ("https://feeds.arstechnica.com/arstechnica/technology-lab", "Ars Technica"),
            # MIT Technology Review AI
            ("https://www.technologyreview.com/feed/", "MIT Tech Review"),
            # ZDNet AI
            ("https://www.zdnet.com/topic/artificial-intelligence/rss.xml", "ZDNet"),
            # InfoQ AI/ML
            ("https://feed.infoq.com/ai-ml-data-eng/", "InfoQ"),
            # Towards Data Science (Medium)
            ("https://towardsdatascience.com/feed", "Towards Data Science"),
        ]
        
        results = []
        now = datetime.now()
        timestamp_threshold = 0
        
        if "24 Hours" in time_span:
            timestamp_threshold = (now - timedelta(hours=24)).timestamp()
        elif "3 Days" in time_span:
             timestamp_threshold = (now - timedelta(days=3)).timestamp()
        elif "7 Days" in time_span:
             timestamp_threshold = (now - timedelta(days=7)).timestamp()

        for url, source_name in rss_urls:
            try:
                feed = feedparser.parse(url)
                if not feed.entries:
                    print(f"  -> {source_name}: 无内容")
                    continue
                
                # Temporary list for this feed
                feed_items = []
                
                for entry in feed.entries:
                    # Check publish date
                    # feedparser converts published to struct_time
                    published_struct = entry.get('published_parsed') or entry.get('updated_parsed')
                    
                    is_within_time = True
                    if published_struct:
                        published_ts = datetime(*published_struct[:6]).timestamp()
                        if published_ts < timestamp_threshold:
                            is_within_time = False
                    
                    # Store item with time flag
                    feed_items.append({
                        "entry": entry,
                        "is_within_time": is_within_time
                    })

                # Filter items
                valid_items = [item['entry'] for item in feed_items if item['is_within_time']]
                
                # Fallback: If 0 items found in time range, take top 3 latest
                if not valid_items and feed_items:
                    print(f"Warning: No RSS items in time range for {source_name}. Taking top 3 latest.")
                    valid_items = [item['entry'] for item in feed_items[:3]]
                elif len(valid_items) > limit:
                    valid_items = valid_items[:limit]

                for entry in valid_items:
                    title = entry.get('title', 'No Title')
                    link = entry.get('link', '')
                    summary = entry.get('summary', '') or entry.get('description', '')
                    
                    # Strip html from summary
                    soup = BeautifulSoup(summary, "html.parser")
                    clean_summary = soup.get_text()[:300] + "..."
                    
                    results.append({
                        "source": source_name,
                        "title": title,
                        "url": link,
                        "summary": clean_summary,
                        "published": entry.get('published', '')
                    })
            except Exception as e:
                print(f"Error fetching RSS {url}: {e}")
        
        # 限制总返回数量，避免过多
        return results[:limit]

    def fetch_reddit_ai(self, limit=15, domains=None, time_span="Last 24 Hours (Fresh)"):
        """获取 Reddit AI 相关 subreddit 的热门帖子"""
        print(f"正在获取 Reddit AI 资讯... Domains: {domains}")
        
        subreddits = [
            "MachineLearning",
            "artificial",
            "LocalLLaMA",
            "singularity",
            "ChatGPT",
            "OpenAI",
        ]
        
        # 根据 domains 筛选相关 subreddit
        if domains:
            if "Robotics" in domains:
                subreddits.append("robotics")
            if "Computer Vision" in domains:
                subreddits.append("computervision")
            if "Programming/SE" in domains:
                subreddits.extend(["learnmachinelearning", "deeplearning"])
        
        results = []
        
        # 根据时间跨度选择排序方式
        time_filter = "day"
        if "3 Days" in time_span:
            time_filter = "week"
        elif "7 Days" in time_span:
            time_filter = "week"
        
        for subreddit in subreddits:
            try:
                # 使用 Reddit JSON API (无需认证)
                url = f"https://www.reddit.com/r/{subreddit}/top.json?t={time_filter}&limit=10"
                response = self.session.get(url, timeout=10)
                
                if response.status_code != 200:
                    print(f"  -> r/{subreddit}: HTTP {response.status_code}")
                    continue
                
                data = response.json()
                posts = data.get('data', {}).get('children', [])
                
                for post in posts:
                    post_data = post.get('data', {})
                    score = post_data.get('score', 0)
                    
                    # 过滤低分帖子
                    min_score = 50 if "Trending" in time_span or "Best" in time_span else 20
                    if score < min_score:
                        continue
                    
                    title = post_data.get('title', '')
                    selftext = post_data.get('selftext', '')[:200] if post_data.get('selftext') else ''
                    
                    results.append({
                        "source": f"Reddit r/{subreddit}",
                        "title": title,
                        "url": f"https://reddit.com{post_data.get('permalink', '')}",
                        "summary": selftext or f"⬆️ {score} | 💬 {post_data.get('num_comments', 0)} comments",
                        "score": score
                    })
                    
            except Exception as e:
                print(f"  -> r/{subreddit} 错误: {e}")
        
        # 按分数排序
        results.sort(key=lambda x: x.get('score', 0), reverse=True)
        return results[:limit]

    def fetch_ai_blogs(self, limit=10, domains=None, time_span="Last 24 Hours (Fresh)"):
        """获取 AI 公司官方博客 RSS"""
        print(f"正在获取 AI 官方博客...")
        
        blog_feeds = [
            # OpenAI Blog
            ("https://openai.com/blog/rss/", "OpenAI Blog"),
            # Google AI Blog
            ("https://blog.google/technology/ai/rss/", "Google AI Blog"),
            # Anthropic
            ("https://www.anthropic.com/feed", "Anthropic"),
            # DeepMind
            ("https://deepmind.google/blog/rss.xml", "DeepMind"),
            # Meta AI
            ("https://ai.meta.com/blog/rss/", "Meta AI"),
            # Hugging Face Blog
            ("https://huggingface.co/blog/feed.xml", "Hugging Face Blog"),
            # LangChain Blog
            ("https://blog.langchain.dev/rss/", "LangChain"),
            # Stability AI
            ("https://stability.ai/feed", "Stability AI"),
        ]
        
        results = []
        now = datetime.now()
        
        # 时间过滤
        if "24 Hours" in time_span:
            timestamp_threshold = (now - timedelta(hours=48)).timestamp()  # 放宽到48小时
        elif "3 Days" in time_span:
            timestamp_threshold = (now - timedelta(days=5)).timestamp()
        else:
            timestamp_threshold = (now - timedelta(days=14)).timestamp()
        
        for url, source_name in blog_feeds:
            try:
                feed = feedparser.parse(url)
                if not feed.entries:
                    continue
                
                for entry in feed.entries[:5]:  # 每个博客取前5篇
                    title = entry.get('title', 'No Title')
                    link = entry.get('link', '')
                    summary = entry.get('summary', '') or entry.get('description', '')
                    
                    # 清理 HTML
                    soup = BeautifulSoup(summary, "html.parser")
                    clean_summary = soup.get_text()[:300] + "..." if len(soup.get_text()) > 300 else soup.get_text()
                    
                    # 检查发布时间
                    published_struct = entry.get('published_parsed') or entry.get('updated_parsed')
                    if published_struct:
                        try:
                            published_ts = datetime(*published_struct[:6]).timestamp()
                            if published_ts < timestamp_threshold:
                                continue
                        except:
                            pass
                    
                    results.append({
                        "source": source_name,
                        "title": title,
                        "url": link,
                        "summary": clean_summary,
                        "published": entry.get('published', '')
                    })
                    
            except Exception as e:
                print(f"  -> {source_name} 错误: {e}")
        
        return results[:limit]

    def fetch_github_trending(self, limit=10, domains=None, time_span="Last 24 Hours (Fresh)"):
        """获取 GitHub Trending 中的 AI/ML 相关项目"""
        print(f"正在获取 GitHub Trending...")
        
        try:
            # 使用非官方的 GitHub Trending API
            url = "https://api.gitterapp.com/repositories?language=python&since=daily"
            response = self.session.get(url, timeout=10)
            
            if response.status_code != 200:
                # 备选方案：直接解析页面
                url = "https://github.com/trending/python?since=daily"
                response = self.session.get(url, timeout=10)
                if response.status_code != 200:
                    return []
                
                soup = BeautifulSoup(response.text, 'html.parser')
                results = []
                
                articles = soup.find_all('article', class_='Box-row', limit=20)
                ai_keywords = ['ai', 'ml', 'llm', 'gpt', 'transformer', 'neural', 'deep', 'learning',
                              'model', 'agent', 'chat', 'vision', 'nlp', 'rag', 'embedding']
                
                for article in articles:
                    h2 = article.find('h2')
                    if h2:
                        a_tag = h2.find('a')
                        if a_tag:
                            repo_path = a_tag.get('href', '').strip('/')
                            repo_name = repo_path.split('/')[-1] if repo_path else ''
                            
                            # 检查是否 AI 相关
                            desc_p = article.find('p')
                            desc = desc_p.get_text(strip=True) if desc_p else ''
                            
                            combined_text = (repo_name + ' ' + desc).lower()
                            if not any(kw in combined_text for kw in ai_keywords):
                                continue
                            
                            # 获取 stars
                            stars_span = article.find('span', class_='d-inline-block float-sm-right')
                            stars = stars_span.get_text(strip=True) if stars_span else ''
                            
                            results.append({
                                "source": "GitHub Trending",
                                "title": repo_path,
                                "url": f"https://github.com/{repo_path}",
                                "summary": f"⭐ {stars} | {desc[:150]}..." if len(desc) > 150 else f"⭐ {stars} | {desc}"
                            })
                
                return results[:limit]
            
            # 如果 API 可用
            data = response.json()
            results = []
            ai_keywords = ['ai', 'ml', 'llm', 'gpt', 'transformer', 'neural', 'deep', 'learning',
                          'model', 'agent', 'chat', 'vision', 'nlp', 'rag', 'embedding']
            
            for repo in data:
                name = repo.get('name', '').lower()
                desc = (repo.get('description', '') or '').lower()
                
                if any(kw in name or kw in desc for kw in ai_keywords):
                    results.append({
                        "source": "GitHub Trending",
                        "title": f"{repo.get('author', '')}/{repo.get('name', '')}",
                        "url": repo.get('url', ''),
                        "summary": f"⭐ {repo.get('stars', 0)} (+{repo.get('currentPeriodStars', 0)} today) | {repo.get('description', '')[:150]}"
                    })
            
            return results[:limit]
            
        except Exception as e:
            print(f"GitHub Trending 错误: {e}")
            return []

    def fetch_producthunt_ai(self, limit=10, domains=None, time_span="Last 24 Hours (Fresh)"):
        """获取 Product Hunt 上的 AI 产品"""
        print(f"正在获取 Product Hunt AI 产品...")
        
        try:
            # 使用网页解析获取 AI 分类产品
            url = "https://www.producthunt.com/topics/artificial-intelligence"
            response = self.session.get(url, timeout=10)
            
            if response.status_code != 200:
                return []
            
            soup = BeautifulSoup(response.text, 'html.parser')
            results = []
            
            # Product Hunt 的结构可能变化，这里做基本解析
            product_cards = soup.find_all('div', {'data-test': 'product-item'}, limit=15)
            
            if not product_cards:
                # 备选选择器
                product_cards = soup.find_all('article', limit=15)
            
            for card in product_cards:
                try:
                    title_elem = card.find('a')
                    if title_elem:
                        title = title_elem.get_text(strip=True)
                        link = title_elem.get('href', '')
                        if not link.startswith('http'):
                            link = f"https://www.producthunt.com{link}"
                        
                        desc_elem = card.find('p')
                        desc = desc_elem.get_text(strip=True) if desc_elem else "AI Product"
                        
                        results.append({
                            "source": "Product Hunt",
                            "title": title,
                            "url": link,
                            "summary": desc[:200]
                        })
                except:
                    continue
            
            return results[:limit]
            
        except Exception as e:
            print(f"Product Hunt 错误: {e}")
            return []

    def fetch_all(self, domains=None, time_span="Last 24 Hours (Fresh)"):
        """聚合所有源"""
        news = []
        
        # 1. Hacker News (高质量讨论)
        news.extend(self.fetch_hacker_news_ai(limit=15, domains=domains, time_span=time_span))
        
        # 2. arXiv 论文 (学术前沿)
        news.extend(self.fetch_arxiv_papers(limit=10, domains=domains, time_span=time_span))
        
        # 3. Hugging Face Daily (模型/论文趋势)
        news.extend(self.fetch_huggingface_daily(domains=domains, time_span=time_span))
        
        # 4. 科技媒体 RSS
        news.extend(self.fetch_tech_news_rss(limit=20, domains=domains, time_span=time_span))
        
        # 5. Reddit AI 社区
        news.extend(self.fetch_reddit_ai(limit=15, domains=domains, time_span=time_span))
        
        # 6. AI 官方博客
        news.extend(self.fetch_ai_blogs(limit=10, domains=domains, time_span=time_span))
        
        # 7. GitHub Trending
        news.extend(self.fetch_github_trending(limit=8, domains=domains, time_span=time_span))
        
        return news

    def fetch_url_content(self, url):
        """抓取单个 URL 的内容"""
        try:
            print(f"正在抓取: {url}")
            response = self.session.get(url, timeout=10)
            if response.status_code != 200:
                return None
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # 尝试获取标题
            title = ""
            if soup.title:
                title = soup.title.string
            else:
                h1 = soup.find('h1')
                if h1:
                    title = h1.get_text(strip=True)
            
            # 尝试获取正文 (简单策略：抓取 <p> 标签)
            paragraphs = soup.find_all('p')
            text_content = ""
            for p in paragraphs:
                text = p.get_text(strip=True)
                if len(text) > 20: # 过滤太短的段落
                    text_content += text + "\n"
            
            # 限制长度
            text_content = text_content[:2000] + "..." if len(text_content) > 2000 else text_content
            
            if not text_content:
                text_content = "无法提取正文内容，仅参考标题。"

            return {
                "title": title or "未知标题",
                "summary": text_content,
                "url": url
            }
        except Exception as e:
            print(f"Error fetching URL {url}: {e}")
            return None

# ===========================
# LLM 处理模块 (Topic & Article)
# ===========================

class LLMProcessor:
    def __init__(self, api_key, base_url, model):
        self.client = OpenAI(api_key=api_key, base_url=base_url)
        self.model = model

    def _load_prompt(self, section_name):
        """Load prompt from prompts.md"""
        try:
            with open('prompts.md', 'r', encoding='utf-8') as f:
                content = f.read()
                
            # Find the section
            start_marker = f"## {section_name}"
            start_index = content.find(start_marker)
            if start_index == -1:
                return None
                
            # Find the next section or end of file
            next_section_index = content.find("## ", start_index + len(start_marker))
            if next_section_index == -1:
                prompt_content = content[start_index + len(start_marker):].strip()
            else:
                prompt_content = content[start_index + len(start_marker):next_section_index].strip()
                
            return prompt_content
        except Exception as e:
            print(f"Error loading prompt from prompts.md: {e}")
            return None

    def generate_topics(self, news_items):
        """将新闻列表转化为选题"""
        if not news_items:
            return []

        # 整理输入文本
        news_text = ""
        for i, item in enumerate(news_items):
            # 为了防止 token 溢出，限制 summary 长度
            summary = str(item.get('summary', ''))[:100]
            news_text += f"{i+1}. [{item['source']}] {item['title']} - {summary}...\n"

        base_prompt = self._load_prompt("Topic Generation")
        if not base_prompt:
            # Fallback if file read fails
            print("Warning: Failed to load Topic Generation prompt from file, using fallback.")
            base_prompt = """
            你是一个专业的科技主编。请根据以下最新的AI新闻列表，构思5-8个适合发布在微信公众号上的深度技术文章选题。
            请严格按照 JSON 格式返回结果。
            """

        prompt = f"""
        {base_prompt}
        
        新闻列表:
        {news_text}
        """

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are a helpful assistant that outputs raw JSON."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7,
                max_tokens=4096
            )
            
            if not response.choices:
                print("LLM Error: No choices returned.")
                return []

            choice = response.choices[0]
            if choice.finish_reason != 'stop':
                print(f"LLM Debug: Finish reason is '{choice.finish_reason}'")

            content = choice.message.content
            
            # 如果 content 为空，可能是因为模型还在思考（如 DeepSeek R1）或者耗尽了 token 用于推理
            if not content:
                print(f"LLM Error: Empty content. Raw message object: {choice.message}")
                return []

            content = content.strip()
            
            # 尝试提取 JSON 数组部分 (查找第一个 [ 和最后一个 ])
            try:
                # 寻找最外层的 []
                start = content.find('[')
                end = content.rfind(']')
                
                json_str = ""
                if start != -1 and end != -1 and end > start:
                    json_str = content[start:end+1]
                elif start != -1:
                    # 找到了 [ 但没找到匹配的 ]，说明被截断了
                    print("Warning: JSON output might be truncated. Attempting to repair...")
                    last_brace = content.rfind('}')
                    if last_brace != -1 and last_brace > start:
                        # 截取到最后一个完整的对象结束符，并闭合数组
                        json_str = content[start:last_brace+1] + "]"
                    else:
                        json_str = content # 无法修复
                else:
                    # 如果没找到 []，尝试清理 markdown
                    clean_content = re.sub(r'^```json\s*', '', content)
                    clean_content = re.sub(r'^```\s*', '', clean_content)
                    json_str = re.sub(r'\s*```$', '', clean_content)
                
                return json.loads(json_str)
            except json.JSONDecodeError as je:
                print(f"JSON Parse Error: {je}")
                # print(f"Raw Content trying to parse:\n{content}")
                return []
        except Exception as e:
            print(f"LLM Topic Generation Error: {e}")
            # Fallback
            return []

    def translate_news_titles(self, news_items, batch_size=20):
        """批量翻译新闻标题 (In-place modification) - 支持分批处理"""
        if not news_items:
            return

        # 加载 Prompt
        base_prompt = self._load_prompt("Title Translation")
        if not base_prompt:
            base_prompt = """
            你是一个专业的科技媒体翻译助手。请将以下 AI 资讯标题列表批量翻译成中文。
            请返回一个 JSON 对象，Key 是输入的序号 ID，Value 是翻译后的中文标题。
            """

        total_items = len(news_items)
        print(f"开始翻译 {total_items} 条标题，分批大小: {batch_size}...")

        # 分批处理
        for start_idx in range(0, total_items, batch_size):
            end_idx = min(start_idx + batch_size, total_items)
            batch_items = news_items[start_idx:end_idx]
            
            print(f"  -> 正在处理第 {start_idx+1} 到 {end_idx} 条...")
            
            # 准备当前批次的输入文本
            titles_text = ""
            for i, item in enumerate(batch_items):
                # 使用全局索引 (1-based) 以保持一致性，或者用批次内索引
                # 这里为了简单对应，使用 batch 内的相对索引 (1-based)，后续再映射回去
                titles_text += f"{i+1}. {item['title']}\n"

            prompt = f"""
            {base_prompt}

            标题列表:
            {titles_text}
            """

            try:
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {"role": "system", "content": "You are a helpful assistant that outputs raw JSON."},
                        {"role": "user", "content": prompt}
                    ],
                    temperature=0.3,
                    max_tokens=4096
                )
                
                content = response.choices[0].message.content
                if not content:
                    print(f"  Translation Batch {start_idx} Error: Empty content")
                    continue

                content = content.strip()
                # 增强的 JSON 清理逻辑
                # 1. 尝试找到第一个 { 和最后一个 }
                s_brace = content.find('{')
                e_brace = content.rfind('}')
                
                if s_brace != -1 and e_brace != -1:
                    json_str = content[s_brace:e_brace+1]
                else:
                    # 只有 Markdown 清理
                    clean = re.sub(r'^```json\s*', '', content)
                    clean = re.sub(r'^```\s*', '', clean)
                    json_str = re.sub(r'\s*```$', '', clean)

                try:
                    translations = json.loads(json_str)
                    
                    # 更新原有 news_items (注意索引偏移)
                    for key, title_zh in translations.items():
                        try:
                            # key 是 batch 内的 1-based index
                            batch_rel_idx = int(key) - 1
                            if 0 <= batch_rel_idx < len(batch_items):
                                # 找到对应的全局 item
                                target_item = batch_items[batch_rel_idx]
                                target_item['title_zh'] = title_zh
                        except ValueError:
                            continue
                            
                except json.JSONDecodeError as je:
                    print(f"  Translation Batch JSON Error: {je}")
                    # print(f"  Raw Content: {content}")
                    
            except Exception as e:
                print(f"  Translation Batch Error: {e}")

    def generate_article(self, topic, related_news_items):
        """基于选题和相关新闻生成文章"""
        
        # 整理上下文
        context_text = ""
        for item in related_news_items:
            context_text += f"=== 来源: {item['source']} ===\n"
            context_text += f"标题: {item['title']}\n"
            context_text += f"链接: {item['url']}\n"
            context_text += f"摘要: {item['summary']}\n\n"
            
        system_prompt = self._load_prompt("Article Generation")
        if not system_prompt:
            print("Warning: Failed to load Article Generation prompt from file, using fallback.")
            system_prompt = """
            你是一位资深 AI 技术布道师，擅长写出深度且通俗易懂的技术文章，适合微信公众号阅读。
            你的文章风格：专业、客观、幽默、干货满满。
            请深入浅出地解释技术原理或新功能亮点。
            """
        
        user_prompt = f"""
        请基于以下选题和参考素材写一篇文章。
        
        【目标选题】
        标题: {topic['title']}
        思路: {topic['description']}
        
        【参考素材】
        {context_text}
        
        请开始写作，输出完整的 Markdown 文章内容。
        """
        
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.7,
                max_tokens=4000
            )
            return response.choices[0].message.content
        except Exception as e:
            return f"Error generating article: {e}"