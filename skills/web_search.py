from skills.skill import Skill
from serpapi import GoogleSearch
import openai
from bs4 import BeautifulSoup
import requests
import re
import time
from googlesearch import search


headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/94.0.4606.81 Safari/537.36"
}

class WebSearch(Skill):
    name = 'web_search'
    description = 'A tool that performs web searches.'
    api_keys_required = [['openai']]

    def __init__(self, api_keys, main_loop_function):
        super().__init__(api_keys, main_loop_function)

    def execute(self, params, dependent_task_outputs, objective):
        # Your function goes here
        
        # Modify the query based on the dependent task output
        if dependent_task_outputs != "":
            dependent_task = f"Use the dependent task output below as reference to help craft the correct search query for the provided task above. Dependent task output:{dependent_task_outputs}."
        else:
            dependent_task = "."
        query = self.text_completion_tool("You are an AI assistant tasked with generating a short and simple Google search query based on the following task: "+params+"."+dependent_task + "\nExample Task: Perform a web search to find reputable sources of news in the field of AI for today's date.\nExample Query:AI News\nExample Task:Perform a search for Yohei Nakajima at Untapped Capital\nExample Query:Yohei Nakajima Untapped Capital\nTask:"+params+"\nQuery:")
        print("\033[90m\033[3m"+"Search query: " +str(query)+"\033[0m")
        # Set the search parameters
        # Perform the web search
        search_results = search(query, sleep_interval=3, num_results=7)
        
        # Simplify the search results
        print("\033[90m\033[3mCompleted search. Now scraping results.\n\033[0m")

        # Store the results from web scraping
        results = ""
        for result in search_results:
            print("\033[90m\033[3m" + "Scraping: "+result+"" + "...\033[0m")
            content = self.web_scrape_tool({"url": result, "task": params,"objective":objective})
            results += str(content) + ". "
        print("\033[90m\033[3m"+str(results[0:100])[0:100]+"...\033[0m")
        # Process the results and generate a report
        results = self.text_completion_tool(f"You are an expert analyst combining the results of multiple web scrapes. Rewrite the following information as one cohesive report without removing any facts. Ignore any reports of not having info, unless all reports say so - in which case explain that the search did not work and suggest other web search queries to try. \n###INFORMATION:{results}.\n###REPORT:")
        time.sleep(1)
        print("DONE!!!")
        return results

    def simplify_search_results(self, search_results):
        simplified_results = []
        for result in search_results:
            simplified_result = {
                 
                "title": result.get("title"),
                "link": result.get("link"),
                "snippet": result.get("snippet")
            }
            simplified_results.append(simplified_result)
        return simplified_results

  
    def text_completion_tool(self, prompt: str):
        messages = [
            {"role": "user", "content": prompt}
        ]
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo-16k",
            messages=messages,
            temperature=0,
            max_tokens=2000,
            top_p=1,
            frequency_penalty=0,
            presence_penalty=0
        )
    
        return response.choices[0].message['content'].strip()


    def web_scrape_tool(self, params):
        content = self.fetch_url_content(params['url'])
        if content is None:
            return None
    
        text = self.extract_text(content)
        print("\033[90m\033[3m"+"Scrape completed. Length:" +str(len(text))+".Now extracting relevant info..."+"...\033[0m")
        info = self.extract_relevant_info(params['objective'], text[0:11000], params['task'])
        links = self.extract_links(content)
        #result = f"{info} URLs: {', '.join(links)}"
        result = info
        
        return result
    
    def fetch_url_content(self,url: str):
        try:
            response = requests.get(url, headers=headers, timeout=10)
            response.raise_for_status()
            return response.content
        except requests.exceptions.RequestException as e:
            print(f"Error while fetching the URL: {e}")
            return ""
    
    def extract_links(self,content: str):
        soup = BeautifulSoup(content, "html.parser")
        links = [link.get('href') for link in soup.findAll('a', attrs={'href': re.compile("^https?://")})]
        return links
    
    def extract_text(self,content: str):
        soup = BeautifulSoup(content, "html.parser")
        text = soup.get_text(strip=True)
        return text
    
    def extract_relevant_info(self, objective, large_string, task):
        chunk_size = 12000
        overlap = 500
        notes = ""
      
        if len(large_string) == 0:
          print("error scraping")
          return "Error scraping."
        
        for i in range(0, len(large_string), chunk_size - overlap):
            
            print("\033[90m\033[3m"+"Reading chunk..."+"\033[0m")  
            chunk = large_string[i:i + chunk_size]
            
            messages = [
                {"role": "system", "content": f"You are an AI assistant."},
                {"role": "user", "content": f"You are an expert AI research assistant tasked with creating or updating the current notes. If the current note is empty, start a current-notes section by exracting relevant data to the task and objective from the chunk of text to analyze. If there is a current note, add new relevant info frol the chunk of text to analyze. Make sure the new or combined notes is comprehensive and well written. Here's the current chunk of text to analyze: {chunk}. ### Here is the current task: {task}.### For context, here is the objective: {objective}.### Here is the data we've extraced so far that you need to update: {notes}.### new-or-updated-note:"}
            ]
    
            response = openai.ChatCompletion.create(
                model="gpt-3.5-turbo-16k",
                messages=messages,
                max_tokens=2000,
                n=1,
                stop="###",
                temperature=0.7,
            )
    
            notes += response.choices[0].message['content'].strip()+". ";
        time.sleep(1)
      
        return notes