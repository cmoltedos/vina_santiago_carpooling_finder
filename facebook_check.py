#!/user/bin/env python3
import os
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import NoSuchElementException
import time
import winsound


EXE_FOLDER = 'E:/Dropbox/Apps/'
GROUPS_IDS = {
	'147488415316365': 'VINA/STGO',
	'1418690655032512': 'Santiago - Vina',
	'stgovina': 'Viajes stgo-vina',
	'1661175270772220': 'VINA/STGO 2018'
}
MIN_BETWEEN_QUERY = 5

def input_args():
	pass


# https://stackoverflow.com/a/23646049
def reverse_readline(filename, buf_size=8192):
    """a generator that returns the lines of a file in reverse order"""
    with open(filename, 'rb') as fh:
        segment = None
        offset = 0
        fh.seek(0, os.SEEK_END)
        file_size = remaining_size = fh.tell()
        while remaining_size > 0:
            offset = min(file_size, offset + buf_size)
            fh.seek(file_size - offset)
            buffer = fh.read(min(remaining_size, buf_size))
            buffer = buffer.decode('utf8', 'ignore')
            remaining_size -= buf_size
            lines = buffer.split('\n')
            # the first line of the buffer is probably not a complete line so
            # we'll save it and append it to the last line of the next buffer
            # we read
            if segment is not None:
                # if the previous chunk starts right from the beginning of line
                # do not concact the segment to the last line of new chunk
                # instead, yield the segment first 
                if buffer[-1] is not '\n':
                    lines[-1] += segment
                else:
                    yield segment
            segment = lines[0]
            for index in range(len(lines) - 1, 0, -1):
                if len(lines[index]):
                    yield lines[index]
        # Don't yield None if the file was empty
        if segment is not None:
            yield segment


def get_cache(group_id, last_n_post=10):
	cache_dict = dict()
	filename = '{folder}cache_fb.csv'.format(folder=EXE_FOLDER)
	if not os.path.exists(filename):
		return cache_dict
	for line in reverse_readline(filename):
		values = line.strip().split(',')
		if values[2] != group_id:
			continue
		cache_dict[(values[0], values[1])] = (values[3], values[4])
		last_n_post -=1 
		if last_n_post <= 0:
			break
	return cache_dict


def save_cache(group_id, post_dict):
	line_format = '{utime},{user},{group},{htime},{comment}\n'
	filename = '{folder}cache_fb.csv'.format(folder=EXE_FOLDER)
	post_list = sorted(post_dict.items())
	with open(filename, 'ab') as cache_file:
		for post in post_list:
			(utime, user), (htime, comment) = post
			try:
				cache_file.write(line_format.format(
					utime=utime, user=user, group=group_id, htime=htime, comment=comment).encode('utf8')
				)
			except UnicodeEncodeError:
				print("Error in line: {line}".format(line=comment))
				raise
	return None


def login(driver, url, user, password):
	driver.get(url)
	wait = WebDriverWait(driver, 10).until(
		EC.visibility_of_element_located((By.ID, 'email')))
	username_element = driver.find_element_by_id('email')
	username_element.send_keys(user)
	password_element = driver.find_element_by_id('pass')
	password_element.send_keys(password)
	button = driver.find_element_by_xpath('//input[@type="submit"]')
	button.click()
	return None


MEM_CACHE = dict()
def get_last_n_post(driver, group_id, n_post=10):
	url = 'https://www.facebook.com/groups/{group_id}/?sorting_setting=CHRONOLOGICAL'
	driver.get(url.format(group_id=group_id))
	wait = WebDriverWait(driver, 10).until(
		EC.visibility_of_element_located((By.XPATH, '//div[@role="feed"]')))
	time.sleep(1)
	global MEM_CACHE
	new_cache_dict = dict()
	if group_id not in MEM_CACHE:
		cache_dict = get_cache(group_id)
		MEM_CACHE[group_id] = cache_dict
	scroll_all_way_down()
	driver.get_screenshot_as_file('main-page.png')
	posts = driver.find_elements_by_css_selector('div[role=article]')
	print("Number of posts: {n_posts}".format(n_posts=len(posts)))
	for num, post in enumerate(posts):
		try:
			author = post.find_elements_by_css_selector('a[data-hovercard*=user]')[-1].get_attribute('innerHTML')
			content = post.find_elements_by_css_selector('div.userContent')[-1].text
			try:
				content = post.find_element_by_css_selector('div.mtm').text
			except NoSuchElementException:
				#import nose.tools;nose.tools.set_trace()
				pass
			content = content.replace(',', '.').replace('\n', '.')
		except IndexError:
			# actions = ActionChains(driver)
			# actions.move_to_element(post).perform()
			# driver.get_screenshot_as_file('main-page_%s.png' % num)
			continue
		
		utimestamp = post.find_elements_by_css_selector('abbr')[-1].get_attribute('data-utime')
		timestamp = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(float(utimestamp)))

		cache_key = (utimestamp, author)
		if cache_key not in MEM_CACHE[group_id]:
			MEM_CACHE[group_id][cache_key] = (timestamp, content)
			new_cache_dict[cache_key] = (timestamp, content)
		else:
			print("[INFO] CACHE HIT")
			break

		line = u'\n{author} (at {timestamp}) says {comment}'.format(
			author=author, timestamp=timestamp, comment=content)
		print(line)
		n_post -= 1
		if n_post <= 0:
			break
	save_cache(group_id, new_cache_dict)
	print("{num} post analyse".format(num=num))
	return num


def scroll_all_way_down():
	last_height = driver.execute_script("return document.body.scrollHeight")
	times = 0
	while times < 10:

		# Scroll down to bottom
		driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")

		# Wait to load page
		time.sleep(0.5)

		# Calculate new scroll height and compare with last scroll height
		new_height = driver.execute_script("return document.body.scrollHeight")
		if new_height == last_height:
			break
		times += 1
	last_height = new_height

if '__main__' == __name__:
	options = webdriver.chrome.options.Options()
	options.add_argument('headless')
	options.add_argument('window-size=1200x600')
	driver = webdriver.Chrome(
		executable_path= '{folder}chromedriver.exe'.format(folder=EXE_FOLDER), 
		chrome_options=options
		)
	#driver.set_window_position(250, 0)

	login(driver, 'https://wwww.facebook.com', os.environ['USER'], os.environ['PASS'])
	#driver.get_screenshot_as_file('main-page.png')
	counter = 0
	while counter < 60:
		for group_id in GROUPS_IDS:
			print("Analyzing group {gname}".format(gname=GROUPS_IDS[group_id]))
			amount = get_last_n_post(driver, group_id, 100)
			if amount > 0:
				winsound.Beep(2500, 500)
		time.sleep(MIN_BETWEEN_QUERY*60)
		counter += 1
	input('End...')
	driver.quit()