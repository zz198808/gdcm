#!/bin/env python
# -*- coding: utf-8 -*-
import sys
import pymysql
import StringIO
import re
import urllib
import simplepool
import random
import easysqllite
import traceback
import datetime
import time
import logging

#微博信息解析类
class MBlogParser(object):
    
	def __init__(self):
		'''init'''
		self.content = ""
		self.result = []
        
	        #划分每条信息
		self.pattern= re.compile(r'<div class="c" id="M_(\S+)">(.*?)</div>(<div class="c">.*?更多热门推荐&gt;&gt;</a></div>)?<div class="s"></div>', re.M)
        
        	#原作无图微博
        	# 1 uid; 2 username; 3 mblog; 5 赞数; 6 转发数; 7 评论数
	        # (8 time: (9 time minite;) | (10 time hour:minute) | (11 year 12 day 12 hour 14 minute)); 16 from
		self.original_no_pic_pattern = re.compile(r'<div><a class="nk" href="http://weibo.cn/?u?/(.*?)\?.*?">(.*?)</a>.*?<span class="ctt">(.*?)(</span>)?                &nbsp;<a href=".*?">赞\[(\d+)\].*?转发\[(\d+)\].*?评论\[(\d+)\].*?<span class="ct">((\d+)分钟前|今天 (\d+:\d+)|(\d+)月(\d+)日 (\d+):(\d+)|\d+-\d+-\d+ \d+:\d+:\d+).*?来自(<.*?>)?(.*?)(</a>)?</span></div>', re.M)
        
        	#转发无图微博
        	# 1.uid; 2.username; 3.mblog; 4.原赞数; 5.原转发数; 6.原评论数; 7.转发理由; 8.赞数; 9.转发数; 10.评论数
        	# (11 time: (12 time minite;) | (13 time hour:minute) | (14 year 15 day 16 hour 17 minute)); 19 from
		self.repost_no_pic_pattern = re.compile(r'<div><a class="nk" href="http://weibo.cn/?u?/(.*?)\?.*?">(.*?)</a>.*?<span class="ctt">(.*?)</span>                &nbsp;<span class="cmt">赞\[(\d+)\].*?原文转发\[(\d+)\].*?原文评论\[(\d+)\].*?</div><div><span class="cmt">转发理由:</span>(.*?)&nbsp;&nbsp;<a href=".*?">赞\[(\d+)\].*?转发\[(\d+)\].*?评论\[(\d+)\]</a>&nbsp;.*?<span class="ct">((\d+)分钟前|今天 (\d+:\d+)|(\d+)月(\d+)日 (\d+):(\d+)|\d+-\d+-\d+ \d+:\d+:\d+).*?来自(<.*?>)?(.*?)(</a>)?</span></div>', re.M)
        
		#原作有图微博
		# 1 uid; 2 username; 3 mblog; 5 赞数; 6 转发数; 7 评论数
		# (8 time: (9 time minite;) | (10 time hour:minute) | (11 year 12 day 12 hour 14 minute)); 16 from
		self.original_with_pic_pattern = re.compile(r'<div><a class="nk" href="http://weibo.cn/?u?/(.*?)\?.*?">(.*?)</a>.*?<span class="ctt">(.*?)(</span>)?                </div><div>.*?原图</a>        &nbsp;<a href=".*?">赞\[(\d+)\]</a>&nbsp;<a href=".*?">转发\[(\d+)\].*?评论\[(\d+)\]</a>&nbsp;.*?<span class="ct">((\d+)分钟前|今天 (\d+:\d+)|(\d+)月(\d+)日 (\d+):(\d+)|\d+-\d+-\d+ \d+:\d+:\d+).*?来自(<.*?>)?(.*?)(</a>)?</span></div>', re.M)
        
		#转发有图微博
		# 1 uid; 2 username; 3 mblog; 4 原微博赞数; 5 原转发数; 6 原评论数; 7 转发理由; 8 赞数; 9 转发数; 10 评论数;
		# (11 time: (12 time minite;) | (13 time hour:minute) | (14 year 15 day 16 hour 17 minute)); 19 from
		self.repost_with_pic_pattern = re.compile(r'<div><a class="nk" href="http://weibo.cn/?u?/(.*?)\?.*?">(.*?)</a>.*?<span class="ctt">(.*?)</span>                    </div><div>.*?原图</a>        &nbsp;<span class="cmt">赞\[(\d+)\].*?原文转发\[(\d+)\].*?原文评论\[(\d+)\]</a></div>.*?<div><span class="cmt">转发理由:</span>(.*?)&nbsp;&nbsp;<a href=".*?">赞\[(\d+)\].*?转发\[(\d+)\].*?评论\[(\d+)\].*?<span class="ct">((\d+)分钟前|今天 (\d+:\d+)|(\d+)月(\d+)日 (\d+):(\d+)|\d+-\d+-\d+ \d+:\d+:\d+).*?来自(<.*?>)?(.*?)(</a>)?</span></div>', re.M)
    
	def setHtml(self, html):
		'''设置被解析页面'''
		self.content = html
    
	def parseTime(self, m):
		'''用于解析时间'''
		now = datetime.datetime.now()
		time = now
		try:
			if m[1]:
				time = now + datetime.timedelta(minutes=-int(m[1]))
			elif m[2]:
				time = datetime.datetime.strptime(m[2], "%H:%M")
				time = time.replace(year=now.year,month=now.month,day=now.day)
			elif m[3]:
				time = time.strptime("%s%s%s%s" % (m[3], m[4], m[5], m[6]), "%m%d%H%M")
				time = time.replace(year=now.year)
			else:
				time = time.strptime(m[0], "%Y-%m-%d %H:%M:%S")
			time = time.strftime("%Y-%m-%d %H:%M")
		except Exception as e:
			traceback.print_exc()
			logger.warn("parse time expected, exception=%s" % e )
		return time
    
	def parse(self):
		'''解析weibo网页'''
		self.result = []
		cont = self.content
		mblog_matchs = self.pattern.finditer(cont)
        
		for item in mblog_matchs:
			wid = item.group(1)
            
			m = self.repost_with_pic_pattern.match( item.group(2) )
			if m:
				time = self.parseTime(m.groups()[10:17])
				# 1 uid; 2 username; 3 mblog; 4 原微博赞数; 5 原转发数; 6 原评论数; 7 转发理由; 8 赞数; 9 转发数; 10 评论数;
				# (11 time: (12 time minite;) | (13 time hour:minute) | (14 year 15 day 16 hour 17 minute) ); 19 from
				row = {
					"type"          :   1,
					"wbid"          :   wid,
					"uid"           :   m.group(1),
					"username"      :   m.group(2),
					"time"          :   time,
					"from"          :   m.group(19),
					"content"       :   m.group(7),
					"comment_count" :   int(m.group(10)),
					"repost_count"  :   int(m.group(9)),
					"attitude_count":   int(m.group(8)),
					"is_original"	:	0,
				}
#				print row
				self.result.append(row)
				continue
            
			m = self.original_with_pic_pattern.match( item.group(2) )
			if m:
				time = self.parseTime(m.groups()[7:14])
				# 1 uid; 2 username; 3 mblog; 5 赞数; 6 转发数; 7 评论数
        			# (8 time: (9 time minite;) | (10 time hour:minute) | (11 year 12 day 12 hour 14 minute)); 16 from
				row = {
					"type"          :   1,
					"wbid"          :   wid,
					"uid"           :   m.group(1),
					"username"      :   m.group(2),
					"time"          :   time,
					"from"          :   m.group(16),
					"content"       :   m.group(3),
					"comment_count" :   int(m.group(7)),
					"repost_count"  :   int(m.group(6)),
					"attitude_count":   int(m.group(5)),
					"is_original"	:	1,
				}
#				print row
				self.result.append(row)
				continue
            
			m = self.repost_no_pic_pattern.match( item.group(2) )
			if m:
				time = self.parseTime(m.groups()[10:17])
				# 1 uid; 2 username; 3 mblog; 4 原微博赞数; 5 原转发数; 6 原评论数; 7 转发理由; 8 赞数; 9 转发数; 10 评论数;
				# (11 time: (12 time minite;) | (13 time hour:minute) | (14 year 15 day 16 hour 17 minute)); 19 from
				row = {
					"type"          :   1,
					"wbid"          :   wid,
					"uid"           :   m.group(1),
					"username"      :   m.group(2),
					"time"          :   time,
					"from"          :   m.group(19),
					"content"       :   m.group(7),
					"comment_count" :   int(m.group(10)),
					"repost_count"  :   int(m.group(9)),
					"attitude_count":   int(m.group(8)),
					"is_original"	:	0,
				}
#				print row
				self.result.append(row)
				continue
            
			m = self.original_no_pic_pattern.match( item.group(2) )
			if m:
				time = self.parseTime(m.groups()[7:14])
				# 1 uid; 2 username; 3 mblog; 5 赞数; 6 转发数; 7 评论数
        			# (8 time: (9 time minite;) | (10 time hour:minute) | (11 year 12 day 12 hour 14 minute)); 16 from
				row = {
					"type"          :   1,
					"wbid"          :   wid,
					"uid"           :   m.group(1),
					"username"      :   m.group(2),
					"time"          :   time,
					"from"          :   m.group(16),
					"content"       :   m.group(3),
					"comment_count" :   int(m.group(7)),
					"repost_count"  :   int(m.group(6)),
					"attitude_count":   int(m.group(5)),
					"is_original"	:	1,
				}
#				print row
				self.result.append(row)
				continue
			logger.warn("not match:"+item.group(2))
		return self.result
		
		
#微博网页爬虫类
class WeiboSpider(object):

	def __init__(self, gsid_file_path):
		'''初始化，读取gsid列表文件'''
		self.gsid_file_path = gsid_file_path
		self.gsids = []
		self.gsid = ""
		
	def read_gsids(self):
		gsid_file = open(self.gsid_file_path,"r")
		self.gsids = gsid_file.readlines()
		
	def generate_gsid(self):
		'''随机生成一个gsid'''
		if not self.gsids:
			self.read_gsids()
		self.gsid = random.choice(self.gsids).strip()
		logger.info("change gsid %s" % self.gsid)
	
	def getPage(self, keyword, page):
		'''获取weibo网页'''
		if not self.gsid:
			self.generate_gsid()
		html = ""
		try:
			while True :
				c = pycurl.Curl()
				c.setopt(c.ENCODING, 'gzip,deflate,sdch')
				c.setopt(c.REFERER, 'http://weibo.cn/search/mblog/')
				c.setopt(c.HTTPHEADER, ["Accept: text/html;q=0.9,*/*;q=0.8", 
					"Accept-Language: zh-cn,zh;q=0.8,en-us;q=0.5,en;q=0.3", 
					'Connection: keep-alive'])
				b = StringIO.StringIO()
				c.setopt(c.WRITEFUNCTION, b.write)
				url="http://weibo.cn/search/mblog?keyword=%s&page=%d&vt=4&gsid=%s" % (keyword, page, self.gsid)
				#print type(url.decode('utf8'))
				c.setopt(c.URL, url)
				c.perform()
				html += b.getvalue()
				b.close()
				c.close()
				if not html:
					self.generate_gsid()
				else:
					return html
		except Exception as e:
			traceback.print_exc()
			logger.warn("get page exception %s, keyword=%s,gsid=%s" % (e, keyword, self.gsid) )
			return None

#数据库工具类
class DBUtil(object):

	def __init__(self, DBParam):
		self.edb = easysqllite.Database(DBParam)
		self.edb.conn.query("SET NAMES UTF8")
    
    	#node_count是部署机器总数，hash_code是本台机器的序列号
	def getProductList(self, node_count, hash_code):
		result = self.edb.conn.read("SELECT a.id, competitor_name from Product a,Competitor b where a.product_name=b.product_name and b.deleted=0 and b.id%%%d=%d" % (int(node_count), int(hash_code)) )
		return result
		
	def inserttoDB(self, row):
#		print row
		row['username'] = self.edb.conn.conn.escape(row['username'])
		row['content'] = self.edb.conn.conn.escape(row['content'])
		row['from'] = self.edb.conn.conn.escape(row['from'])
		sql = '''INSERT INTO Message SET
			wbid = '%(wbid)s', 
			userid = '%(uid)s', 
			username = %(username)s, 
               		time = '%(time)s', 
               		content = %(content)s, 
               		`from` = %(from)s, 
               		type = %(type)d,
               		comment_count = %(comment_count)d,
               		repost_count = %(repost_count)d,
               		attitude_count = %(attitude_count)d,
			is_original = %(is_original)d
			on duplicate key update 
			comment_count = %(comment_count)d,
			repost_count = %(repost_count)d,
			attitude_count = %(attitude_count)d''' % row 
		
		try:
			self.edb.conn.query(sql)
		except Exception as e:
			traceback.print_exc()
			logger.warn( "DataBase operate exception %s" % e )

#运行线程函数
def run(keyword, start, end):
	
	dbutil = DBUtil(DBParam)
	weiboSpider = WeiboSpider('gsid.txt')
	mBlogParser = MBlogParser()
    
	count = 0
    	for i in range(start, end):
		html = weiboSpider.getPage(keyword, i)
		if html:
			#print count	
			mBlogParser.setHtml(html)
			row_list = mBlogParser.parse()
			#一旦发现没有信息的网页就退出
			if not row_list:
				return
			for row in row_list:
#				print row
				dbutil.inserttoDB(row)
				count += 1
		time.sleep(0.1)
	logger.info( "insert %d weibo" % count )

#主函数    
if __name__ == '__main__' :
	sys.path.append('~/wfb/spider/pycurl/lib/python2.7/site-packages/')
	import pycurl

    	#total node count
	node_count = sys.argv[1]
	#hash_code
	hash_code = sys.argv[2]
    
	DBParam = {
		"host"  :    "cq01-dt-olaptest01.xxx",
		"port"  :    8484,
		"user"  :    "root",
		"passwd":    "",
		"db"       :    'weibo',
        	"charset": 'utf8',
	}
    
	logger = logging.getLogger()
	loghandler = logging.FileHandler( "./log/spider_%s.log" % datetime.datetime.now().date() )
	logformat = logging.Formatter('%(asctime)s %(levelname)s %(message)s')
	loghandler.setFormatter(logformat)
	logger.addHandler(loghandler)
	logger.setLevel(logging.NOTSET)
	logger.info("init log")
    
	dbutil = DBUtil(DBParam)
	search_list = dbutil.getProductList(node_count, hash_code)
    
	pool = simplepool.WorkerPool(5) 

	for search in search_list:
		keyword = search["competitor_name"].encode('utf8')
#print keyword
    		#5个线程，每个线程一次处理10个网页，发现没有信息的，退出
		for i in range(0, 10):
			pool(lambda start = i*10, end = (i+1)*10: run(keyword, start, end))
		pool.join()
    
	
