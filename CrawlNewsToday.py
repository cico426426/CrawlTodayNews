from concurrent.futures import thread
from multiprocessing import Semaphore
import queue
import threading
import datetime
import time
import requests
import bs4 
from threading import Thread
from typing import List
import csv

class Worker(threading.Thread):
	def __init__(self, queue, semaphore, file='today.csv'):
		threading.Thread.__init__(self)
		self.queue = queue
		self.semaphore = semaphore
		self.file = file
	
	def run(self):
		while self.queue.empty() == False:
			line = self.queue.get()
			self.semaphore.acquire()
			write_file(line, self.file)
			time.sleep(7)
			self.semaphore.release()

def clear_file(fname):
	try:
		with open(fname, 'a', encoding='utf-8-sig') as f:
			f.truncate(0)
	except IOError as e:
		print(f"Couldn't open or write to file ({e})") 

def write_file(msg, fname):
	
	try:
		with open(fname, 'a', encoding='utf-8-sig') as f:
			csvWriter = csv.writer(f)
			csvWriter.writerow(msg)
	except IOError as e:
		print(f"Couldn't open or write to file ({e})") 


def get_Page_Soup(page : int, session):
	url = 'https://news.pts.org.tw/dailynews'
	html = session.get(url, params={
			'page' : page
		})
	return bs4.BeautifulSoup(html.text, 'lxml')

def get_news_soup(url : str, session):
	html = session.get(url)
	return bs4.BeautifulSoup(html.text, 'lxml')
	
def get_news_List(page :  int, session) -> List:
	res = []
	req_thread_list = []
	for p in range(1, page):
		req_thread = Thread(target=get_news_info, args=(p, res, session))
		req_thread.start()
		req_thread_list.append(req_thread)
		time.sleep(2)
	
	for thread in req_thread_list:
		thread.join()
	return res

def get_news_info(p : int, res : List, session):
	soup = get_Page_Soup(p, session)
	news_list = soup.find_all('h2')
	for news in news_list:
		res.append([news.getText(), news.find('a', href=True)['href']])
	

def get_all_news_point(news_list : List, session)->List:
	point_list = []
	req_thread_list = []

	for news in news_list:
		req_thread = Thread(target=get_news_point, args=(news[1], point_list, session))
		req_thread.start()
		req_thread_list.append(req_thread)
		time.sleep(2)
	for req_thread in req_thread_list:
		req_thread.join()
	return point_list

def get_news_point(url : str, point_list : List, session):
	soup = get_news_soup(url, session)
	point = soup.select('.articleimg')
	if len(point) == 0:
		point_list.append('還沒有結論')
		return 
	point_list.append(point[0].text.strip())

def get_Today_Pages(today : str, session)->int:
	for p in range(1, 10):
		soup = get_Page_Soup(p, session)
		date = soup.select('.break-news-time')[0].text.strip()
		if date != today.strip():
			return p


# 寫入順序被插隊， 未解決
def output_news(news_queue): 
	clear_file('today.csv')
	semaphore = threading.Semaphore(2)
	threads = []
	for i in range(6):
		worker = Worker(news_queue, semaphore)
		worker.start()
		threads.append(worker)
	for thread in threads:
		thread.join()


if __name__ == '__main__':
	dt = datetime.datetime.today()
	today = str(dt.month) +' 月 '+ str(dt.day) +' 日' 
	req_session = requests.Session()
	page = get_Today_Pages(today, req_session)
	news_list = get_news_List(page, req_session)
	point_list = get_all_news_point(news_list, req_session)

	news_queue = queue.Queue()

	for i, news in enumerate(news_list):
		news_queue.put([news[0], news[1], point_list[i]])

	output_news(news_queue)
	

	