import urllib.request
import urllib.parse
import json
import ssl
import time

def classplus_login(email, password, org_code=""):
    base_url = "https://api.classplusapp.com/v2"
    url = f"{base_url}/users/login"
    
    payload = {"email": email, "password": password}
    if org_code:
        payload["orgCode"] = org_code
        
    data = json.dumps(payload).encode('utf-8')
    
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    
    headers = {
        'User-Agent': 'okhttp/4.9.1',
        'device-type': 'ANDROID',
        'device-id': 'dummy-id',
        'api-version': '50',
        'app-version': '1.4.152.1',
        'Content-Type': 'application/json'
    }
    if org_code:
        headers['orgcode'] = org_code
        
    try:
        req = urllib.request.Request(url, data=data, headers=headers, method='POST')
        with urllib.request.urlopen(req, context=ctx, timeout=10) as res:
            if res.status == 200:
                resp_json = json.loads(res.read().decode('utf-8'))
                if resp_json.get('status') == 'success' or resp_json.get('data'):
                    return {"success": True, "data": resp_json.get('data', resp_json), "endpoint": "/users/login"}
    except urllib.error.HTTPError as e:
        try:
            err_data = json.loads(e.read().decode())
            return {"success": False, "error": err_data.get('message', f"HTTP {e.code}")}
        except:
            return {"success": False, "error": f"HTTP {e.code}"}
    except Exception as e:
        return {"success": False, "error": str(e)}
            
    return {"success": False, "error": "Login failed."}

def classplus_get_courses(token, org_code=""):
    import cloudscraper
    base_url = "https://api.classplusapp.com/v2"
    url = f"{base_url}/courses"
    
    headers = {
        'User-Agent': 'okhttp/4.9.1',
        'x-access-token': token,
        'Content-Type': 'application/json',
        'api-version': '50'
    }
    if org_code:
        headers['orgcode'] = org_code
        
    try:
        scraper = cloudscraper.create_scraper()
        res = scraper.get(url, headers=headers, timeout=15)
        if res.status_code == 200:
            resp_json = res.json()
            courses = resp_json.get('data', {}).get('courses', [])
            if courses:
                return {"success": True, "courses": courses}
    except Exception as e:
        pass
            
    return {"success": False, "error": "Failed to fetch courses."}

def extract_batch_links(token, course_id, org_code="", bot_instance=None, chat_id=None):
    base_url = "https://api.classplusapp.com/v2"
    all_links = []
    import cloudscraper
    
    headers = {
        'User-Agent': 'okhttp/4.9.1',
        'x-access-token': token,
        'Content-Type': 'application/json',
        'api-version': '50'
    }
    if org_code:
        headers['orgcode'] = org_code

    scraper = cloudscraper.create_scraper()

    def fetch_folder(folder_id, path_prefix=""):
        offset = 0
        limit = 100
        while True:
            url = f"{base_url}/course/content/get?courseId={course_id}&folderId={folder_id}&limit={limit}&offset={offset}"
            try:
                res = scraper.get(url, headers=headers, timeout=15)
                if res.status_code == 200:
                    items = res.json().get('data', {}).get('courseContent', [])
                    if not items:
                        break
                        
                    for item in items:
                        title = item.get('name', 'Unknown')
                        res_type = int(item.get('contentType', 0))
                        item_id = item.get('id')
                        
                        if res_type == 1: # Folder
                            if bot_instance and chat_id and offset == 0:
                                try:
                                    bot_instance.send_message(chat_id, f"📂 Scanning folder: {title}")
                                except Exception: pass
                            fetch_folder(item_id, path_prefix + title + " > ")
                        elif res_type == 2: # Video
                            vid_url = item.get('url')
                            if not vid_url and item.get('thumbnailUrl'):
                                vid_url = item.get('thumbnailUrl')
                                import re
                                vid_url = re.sub(r'thumbnail\.png$', 'master.m3u8', vid_url)
                                vid_url = re.sub(r'\.jpeg$', '/master.m3u8', vid_url)
                                vid_url = re.sub(r'\.jpg$', '/master.m3u8', vid_url)
                            if vid_url: all_links.append(f"{title}:{vid_url}")
                        elif res_type == 3: # PDF/Doc
                            pdf_url = item.get('url')
                            if pdf_url: all_links.append(f"{title}:{pdf_url}")
                            
                    offset += limit
                else:
                    if bot_instance and chat_id and offset == 0:
                        try:
                            bot_instance.send_message(chat_id, f"❌ Classplus API Error: {res.status_code} - {res.text[:50]}")
                        except Exception: pass
                    break
            except Exception as e:
                if bot_instance and chat_id and offset == 0:
                    try:
                        bot_instance.send_message(chat_id, f"❌ Exception: {str(e)}")
                    except Exception: pass
                break

    fetch_folder("0")
    return all_links
