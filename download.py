import pandas as pd
import numpy as np

import time
import os
import sys
import git
import json as js

import requests

import multiprocessing
import multiprocessing.pool
from multiprocessing import Process, Queue, Pool
import concurrent.futures

from pyquery import PyQuery as pq
from selenium import webdriver
from selenium.webdriver.chrome.options import Options

import subprocess

from distutils.dir_util import copy_tree

from tqdm import tqdm

apple = "/Volumes/SL-E1/2019_Summer_Project/repo4/"

ubuntu = "/media/lofowl/SL-E1/2019_Summer_Project/repo4/"

class NoDaemonProcess(multiprocessing.Process):
    # make 'daemon' attribute always return False
    def _get_daemon(self):
        return False
    def _set_daemon(self, value):
        pass
    daemon = property(_get_daemon, _set_daemon)

# We sub-class multiprocessing.pool.Pool instead of multiprocessing.Pool
# because the latter is only a wrapper function, not a proper class.
class MyPool(multiprocessing.pool.Pool):
    Process = NoDaemonProcess

def sha_filter_p(lock, q, platform):
    not_finish = True
    while not_finish:
        lock.acquire()
        not_finish = not q.empty()
        if not_finish:
            name = q.get(False)
        lock.release()
        print(name)

        try:
            git_url = "github.com/%s.git" % name
            readme_url = "https://api.github.com/repos/%s/readme"%name
            start = time.time()

            switch = name.split("/")
            switch_name = name.replace("/","#")
            save_to = platform+switch_name+"/"
            repo = save_to+switch[-1]

            print(save_to)
            print(repo)

            get_clone(git_url,save_to)

            if len(os.listdir(platform+switch_name)) == 0:
                print(platform+switch_name)
                os.system("rm -rf "+platform+switch_name)
                continue
            else:
                os.chdir(repo)
                os.system("nbstripout --install")

            repos = git.Repo.init(path=repo)

            get_commits_details(repos,save_to)
            print("@@@@@@@@@@@@@@@@@@@@@@@@%s done details.csv"%name)

            get_repo_details(name,repos,save_to,repo)
            print("########################%s done data.txt"%name)

            get_files_size(repos,save_to)
            print("$$$$$$$$$$$$$$$$$$$$$$$$%s done files.csv"%name)

            get_readme(readme_url,save_to)
            print("^^^^^^^^^^^^^^^^^^^^^^^^^1%s done readme.txt"%name)

            get_commit_change_types(switch,repo,repos,save_to)
            print("***************************%s done commit_change.csv"%name)

            #os.system('rm -rf '+repo)
            end = time.time()
            print(end-start)
        except:
            print("!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!! %s"%(name))

def get_clone(url,save_to):
    os.mkdir(save_to)
    os.chdir(save_to)
    os.system("git clone https://@"+url)

def get_all_commits(repos):
    stat = repos.git.log(all=True,full_history=True,no_merges=True,pretty="%H")
    stat = stat.split("\n")
    return len(set(stat))

def get_all_ipynb_commits(repos):
    stat = repos.git.log("*.ipynb",all=True,full_history=True,no_merges=True,follow=True,pretty="%H")
    stat = stat.split("\n")
    return len(set(stat))

def get_last_commits_time(repos,repo):
    os.chdir(repo)
    os.system("git checkout master")
    time = repos.git.show(pretty="%cd",name_only=True)
    time = time.split("\n")
    return time[0]

def get_repo_details(name,repos,save_to,repo):
    json_data = {}
    url = "https://api.github.com/repos/"+name
    url_con = url+"/contributors?page="
    url_topics = url+"/topics"
    url_languages = url+"/languages"

    check = True
    url_web = "https://www.github.com/"+name
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    if sys.platform == "darwin":
        path = "/Volumes/SL-E1/2019_Summer_Project/code/codes_3/chromedriver"
    else:
        path = "chromedriver"
    broswer = webdriver.Chrome(path,chrome_options = chrome_options)
    broswer.get(url_web)
    html = broswer.page_source
    doc = pq(html)
    get_url = doc('.numbers-summary').items()
    for i in get_url:
        i = i.remove_namespaces()
        info = i('span').text()
    info = info.split()
    if len(info) != 4:
        data = response(url_web)
        doc = pq(data.content)
        get_url = doc('.numbers-summary').items()
        for i in get_url:
            i = i.remove_namespaces()
            info = i('span').text()
        info = info.split()
    broswer.close()
    print("%s %s"%(name,info))

    json_data["commits_count"] = get_all_commits(repos)
    json_data["commits_ipynb_count"] = get_all_ipynb_commits(repos)
    data = js.loads(response(url).content)
    json_data["branch"] = info[1]
    json_data["release"] = info[2]
    json_data["contributors"] = info[3]
    json_data["description"] = data["description"]
    top = js.loads(response(url_topics).content)
    json_data["topics"] = top["names"]
    json_data["forks"] = data["forks_count"]
    json_data["watch"] = data["subscribers_count"]
    json_data["stars"] = data["stargazers_count"]
    json_data["languages"] = js.loads(response(url_languages).content)

    json_data["create_time"] = get_last_commits_time(repos,repo)



    with open(save_to+'data.txt', 'w') as outfile:
        js.dump(json_data, outfile)

def get_commits_details(repos,save_to):
    filter_sha = repos.git.log('*.ipynb', follow=True, all=True, full_history=True, pretty="%H", no_merges=True)
    filter_sha = filter_sha.split("\n")
    filter_sha = list(set(filter_sha))

    details_list = []

    for aid in filter_sha:
        if aid == "":
            break
        sha = repos.git.show(aid,full_history=True, name_status=True,no_merges=True, pretty="%an^$#%ae^$#%ad^$#%cn^$#%ce^$#%cd^$#%s")
        if len(sha) != 0:
            lists = sha.split("\n")
            details = lists[0].split("^$#")
            details = [aid] + details
            lists.pop(0)
            lists.pop(0)
            ipynb_count = 0
            others_count = 0
            total_count = 0
            files = ""
            for i in lists:
                if ".ipynb" in i:
                    files += i+"$"
                    ipynb_count += 1
                else:
                    others_count += 1
                total_count += 1

            details.append(ipynb_count)
            details.append(others_count)
            details.append(total_count)
            details.append(files)

            details_list.append(details)

    if len(details_list) != 0:
        details_name = ["sha", "author.name", "author.email", "author.date", "commiter.name","commiter.email","committer.date","commit.message","ipynb.count","others.count","total.count","ipynb"]
        pc = pd.DataFrame(data=details_list, columns=details_name)
        pc.to_csv(save_to+"details.csv", index=0)

def get_readme(url,save_to):
    req = response(url)
    data = js.loads(req.content)
    download_url = ""
    try:
        download_url = data["download_url"]
        print(donlowad_url)
    except:
        pass
    if download_url != "":
        r = response(data["download_url"])
        with open(save_to+"readme.md", "wb") as code:
            code.write(r.content)

def sizeUtils(name,repos):
    diff = repos.git.log('--',name,full_history=True,p=True,no_merges=True,pretty="%H^&*%cd")
    diff = diff.split("\n")
    final_list = []
    child_list = []
    add_str = ""
    add_count = 0
    neg_str = ""
    neg_count = 0
    for i in diff:
        if "^&*" in i:
            if len(child_list) != 0:
                child_list.append(add_count)
                child_list.append(neg_count)
                if add_count == 0 and neg_count == 0:
                    child_list.append(-1)
                else:
                    child_list.append(round(diff_chunk_size(sys.getsizeof(add_str),sys.getsizeof(neg_str))))
                final_list.append(child_list)
            child_list = []
            add_str = ""
            add_count = 0
            neg_str = ""
            neg_count = 0
            i = i.split("^&*")
            child_list.append(name)
            child_list.append(i[0])
            child_list.append(i[1][:-6])
        elif i != "":
            if i[0] == "+" and i[1] != "+":
                add_str += str(i[1:])
                add_count += 1
            elif i[0] == "-" and i[1] != "-":
                neg_str += str(i[1:])
                neg_count += 1
    child_list.append(add_count)
    child_list.append(neg_count)
    child_list.append(round(diff_chunk_size(sys.getsizeof(add_str),sys.getsizeof(neg_str))))
    final_list.append(child_list)
    return final_list

def statuUtils(name,repos):
    diff = repos.git.log('--',name,full_history=True,name_status=True,no_merges=True,pretty="")
    diff = diff.split("\n")
    final_list = []
    for i in diff:
        if i !="":
            i = i.split()
            final_list.append(i[0])

    return final_list

def countUtils(name,repos):
    diff = repos.git.log('--',name,full_history=True,numstat=True,no_merges=True,pretty="")
    diff = diff.split("\n")
    final_list = []
    for i in diff:
        child_list = []
        i = i.split()
        child_list.append(i[0])
        child_list.append(i[1])
        final_list.append(child_list)
    return final_list

def add_deletetion_count_Utils(name,repos):
    diff = repos.git.log('--',name,full_history=True,numstat=True,no_merges=True,pretty="")
    diff = diff.split("\n")
    final_list = []

    return final_list

def combain(lists):
    try:
        name = lists[0]
        repos = lists[1]
        final_list = sizeUtils(name,repos)
        statu_list = statuUtils(name,repos)
        count_list = countUtils(name,repos)
        for i in range(len(final_list)):
            for j in count_list[i]:
                final_list[i].append(j)
            final_list[i].append(statu_list[i])
        return final_list
    except Exception as e:
        return []

def diff_chunk_size(a,r):
    lower_bound = max(a,r)
    upper_bound = a+r
    return (lower_bound + upper_bound)/2

def get_files_size(repos,save_to):
    startfff = time.time()
    stat = repos.git.log("*.ipynb",full_history=True,follow=True,name_only=True,no_merges=True,pretty="")
    stat = stat.split("\n")

    stat = list(set(stat))
    print(len(stat))

    switch_list = []
    for i in stat:
        child_list = []
        child_list.append(i)
        child_list.append(repos)
        switch_list.append(child_list)


    final_list = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=12) as executor:
        files_list = list(executor.map(combain,switch_list))

    final_list = []
    for i in files_list:
        if len(i) != 0:
            final_list += i

    print(len(final_list))
    endfff = time.time()
    print(endfff -startfff)

    details_name = ["name", "sha", "date", "input_addition", "input_deletion","size","total_addition","total_deletioni","status"]
    pc = pd.DataFrame(data=final_list,columns=details_name)
    pc.to_csv(save_to+"files.csv",index=0)

def get_commit_change_types(switch,repo,repos,save_to):
    path = save_to
    file = repo

    stat = repos.git.log("*.ipynb",all=True,full_history=True,no_merges=True,follow=True,pretty="%H")
    stat = stat.split("\n")
    stat = list(set(stat))
    if len(stat) >= 50:
        N = 5
        stat_list = np.array_split(stat,N)
    else:
        N = 1
        stat_list = [stat]

    start = time.time()
    statinfo = os.stat(file)
    print(statinfo.st_size)


    for i in range(N-1):
        copy_file = repo+str(i)
        copy_tree(file,copy_file)

    end = time.time()
    download_time = end - start


    repos_list = []
    path_list = []
    files_name = os.listdir(path)
    print(files_name)
    for i in files_name:
        print(i)
        if switch[1] in i:
            new_path = path +i
            repos_list.append(git.Repo.init(path=new_path))
            path_list.append(new_path)

    input = list(zip(repos_list,stat_list,path_list))
    start = time.time()
    final_list = []
    with concurrent.futures.ProcessPoolExecutor(max_workers=N) as executor:
        print("get into sub_run")
#        files_list = list(executor.map(sub_run,input))
        try:
            files_list = list(executor.map(sub_run,input))
        except Exception as e:
            print(e)
    final_list = []
    for i in files_list:
        if len(i) != 0:
            final_list += i


    columns_name = ["sha",
                    "status",
                    "parent_index",
                    "child_index",
                    "file",
                    "types"]
    pa = pd.DataFrame(final_list,columns=columns_name)
    pa.to_csv(save_to+"change.csv",index=0)
    end = time.time()
    runtime = end - start
    finaltime = download_time + runtime

    for i in path_list:
        os.system("rm -rf "+i)

def get_status(target_sha,repos):
    check = repos.git.show(target_sha,"*.ipynb",pretty="",name_status=True,follow=True)
    check = check.split("\n")

    lists = []
    for i in check:
        i = i.split()
        if i[0] == "M":
            lists.append(i[1])
    return lists

def check_sources(target_sha,repos,path):
    sha = repos.git.show(target_sha,pretty="raw",name_only=True,no_merges=True)
    sha = sha.split("\n")

    parent_sha = ""
    for i in sha:
        if "parent" in i:
            i = i.split()
            try:
                parent_sha = i[1]
            except:
                return[(target_sha,"notp",0,0,0,0)]
            break

    if parent_sha == "":
        return [(target_sha,"notp",0,0,0,0)]

    child_files = repos.git.show(target_sha,"*.ipynb",full_history=True,pretty="",name_only=True,follow=True)
    child_files = child_files.split("\n")

    parent_files = repos.git.show(parent_sha,"*.ipynb",full_history=True,pretty="",name_only=True,follow=True)
    parent_files = parent_files.split("\n")

    os.chdir(path)

    status_lists = get_status(target_sha,repos)

    try:
        if len(status_lists) != 0:
            os.system("git checkout -f %s"%target_sha)
            commond = "nbdiff -s %s %s"%(parent_sha,target_sha)
            diff = subprocess.check_output(commond,shell=True)
            diff = diff.decode("utf-8").split("\n")
        else:
            return [(target_sha,"notm",0,0,0,0)]

    except Exception as e:
        return [(target_sha,"error",0,0,0,0)]
        diff = []

    if len(diff) == 0:
        return [(target_sha,"notr",0,0,0,0)]

    types = []
    indexes = []
    new_indexes = []
    files_neg = []
    files_pos = []

    files_list = []
    target_value = []
    file_name_pos = ""
    file_name_neg = ""
    isFirst = False
    filename =""
    number_in_front = 0

    count = 0
    for pointer in range(len(diff)):
        if "---" in diff[pointer]:
            get_name = diff[pointer].split(" ")
            if len(get_name) >= 3:
                if ".ipynb" in get_name[1]:
                    number_in_front = 0
                    file_name_neg = get_name[1]
                elif "/dev/null" in get_name[1]:
                    number_in_front = 0
                    file_name_neg = "added"

        if "+++" in diff[pointer]:
            get_name = diff[pointer].split(" ")
            if len(get_name) >= 3:
                if ".ipynb" in get_name[1]:
                    file_name_pos = get_name[1]

                elif "/dev/null" in get_name[1]:
                    file_name_pos = "delete"

                if get_name[1] in status_lists:
                    isFirst = True
                else:
                    isFirst = False

        if isFirst:
            if "##" in diff[pointer]:
                value = diff[pointer][:-5]
                value = value[5:]
                value = value.split(" ")
                try:
                    if value[1] in ['modified','inserted','deleted','raw','added']:
                        if value[1] == 'modified':
                            files_neg.append(file_name_neg)
                            files_pos.append(file_name_pos)
                            types.append(value[1])
                            get_index = value[-1].split("/")
                            for j in get_index:
                                if j.isdigit():
                                    indexes.append(j)
                                    new_indexes.append(int(j)+number_in_front)
                                    target_value.append("none")
                        elif value[1]in ['inserted','added']:
                            containPlus = True
                            con_pointer = pointer
                            inserted_count = 0
                            start_index = 0
                            get_index = value[-1].split("/")
                            for j in get_index:
                                if j.isdigit():
                                    start_index = int(j)
                            while containPlus:
                                con_pointer += 1
                                check_plus = diff[con_pointer]
                                if "+" in check_plus:
                                    check_plus = check_plus.split(" ")
                                    try:
                                        if check_plus[2] in ['markdown','code','raw']:
                                            files_neg.append(file_name_neg)
                                            files_pos.append(file_name_pos)
                                            types.append(value[1])
                                            indexes.append(start_index)
                                            new_indexes.append(start_index+inserted_count+number_in_front)
                                            target_value.append(check_plus[2])
                                            inserted_count += 1
                                    except:
                                        pass
                                else:
                                    containPlus = False
                            number_in_front += inserted_count
                        elif value[1] == 'deleted':
                            get_index = value[-1].split("/")
                            start_index = 0
                            for j in get_index:
                                if j.isdigit():
                                    start_index = int(j)
                                elif any(k.isdigit() for k in j):
                                    j = j.split("-")
                                    start_index = j[0]
                            deleted_count = 0
                            containMinus = True
                            con_pointer = pointer
                            while containMinus:
                                con_pointer += 1
                                check_minus = diff[con_pointer]
                                if "-" in check_minus:
                                    check_minus = check_minus.split(" ")
                                    try:
                                        if check_minus[2] in ['markdown','code','raw']:
                                            files_neg.append(file_name_neg)
                                            files_pos.append(file_name_pos)
                                            types.append('deleted')
                                            indexes.append(int(start_index)+deleted_count)
                                            new_indexes.append(-1)
                                            target_value.append(check_minus[2])
                                            deleted_count += 1

                                    except:
                                        pass
                                else:
                                    containMinus = False
                            number_in_front -= deleted_count
                except:
                    pass

    os.system("git checkout -f %s"%parent_sha)
    final_files = []
    for i in range(len(files_neg)):
        if files_neg[i] not in ["","/dev/null"]:
            final_files.append(files_neg[i])
        else:
            final_files.append(files_pos[i])
    all_name = list(set(final_files))

    files_list = []
    for i in all_name:
        if i != '/dev/null':
            try:
                commond = "nbshow -s %s"%i
                diff = subprocess.check_output(commond,shell=True)
                diff = diff.decode("utf-8").split("\n")
                files_list.append(diff)
            except:
                files_list.append([])
        else:
            files_list.append([])

    #for i in range(300):
    #    print(diff[i])
    for pointer in range(len(target_value)):
        if target_value[pointer] == "none":
            for i in files_list[all_name.index(final_files[pointer])]:
                if "code cell" in i:
                    i = i.split()
                    if i[2][:-1] == indexes[pointer]:
                        target_value[pointer] = "code"
                        break
                elif "markdown cell" in i:
                    i = i.split()
                    if i[2][:-1] == indexes[pointer]:
                        target_value[pointer] = "markdown"
                        break
                elif "raw cell" in i:
                    i = i.split()
                    if i[2][:-1] == indexes[pointer]:
                        target_value[pointer] = "raw"
                        break

    if len(target_value) != 0:
        commit = [target_sha for i in range(len(types))]
        a = list(zip(commit,types,indexes,new_indexes,final_files,target_value))
        return a
    else:
        return [(target_sha,"notr",0,0,0,0)]

def sub_run(data):
    repos = data[0]
    stat = data[1]
    path = data[2]
    stat = list(set(stat))
    print(repos)
    print(path)

    final_list = []
    error_list = []
    empty_list = []

    for i in stat:
        data = check_sources(i,repos,path)
        if len(data) != 0:
            final_list += data
        else:
            empty_list.append(i)

    return final_list

def response(url):
    while True:
        try:
            req = requests.get(url, headers=selectKeys(), timeout=None)
            return req
        except:
            time.sleep(10)

def checkTimes(types, new_tokens):
    local_url = "https://api.github.com/rate_limit"
    data = js.loads(requests.get(local_url, headers=new_tokens, timeout=None).content)
    try:
        if types:
            check = data["resources"]["core"]["remaining"] <= 64
            return check
        else:
            print(data["resources"]["core"]["remaining"])
            return True
    except:
        return True

def selectKeys():
    token_list = ['fc063d4037053732ff7788d24d78ef4db1bd5cee',
                  '20699cb5df6f919c637f88f131d8711362e602ee',
                  'db1df7351ac57479a08b8c6cab5a5e20777879c0',
                  'c453483b5bd54664e6af50be623b3cc5864eb642',
                  '2a53377700d00b71bf8a380bac2045abec4fa147',
                  'f9ee420b58da2078b974ea129db5a4597edef7a0',
                  '35cd8c93b2d1bdf7de31521a538377fe697cb8c6',
                  '598c3ff419779d73bd09f6bb4848ca42d0c0cb8d',
                  'bc9cfe5009096052a6cc29273e8dec7c74b23f86']
    while True:
        for i in token_list:
            tokens = {
                'Authorization': 'token ' + i,
                "Accept": "application/vnd.github.mercy-preview+json",
                'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_10_1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/39.0.2171.95 Safari/537.36'
            }
            if not checkTimes(True, tokens):
                return tokens
        print("Reach limit")
        time.sleep(300)

def check_files(platform,name):
    try:
        name = name.replace("/","#")
        if os.path.exists(platform+name):
            return False
        else:
            return True
    except:
        return True

def multi_processing():
    if sys.platform == "darwin":
        platform = apple
        url = "/Volumes/SL-E1/2019_Summer_Project/filter_notebooks.csv"
    else:
        platform = ubuntu
        url = "/media/lofowl/SL-E1/2019_Summer_Project/filter_notebooks.csv"
    print(sys.platform)
    print(platform)

    #redo_exits_folder()
    data = pd.read_csv(url, header=None)
    data = np.array(data[[1]]).tolist()
    data = list(map(lambda x: x[0], data))

    data = list(map(lambda x: x[29:], data))
    manager = multiprocessing.Manager()
    q = manager.Queue()
    lock = manager.Lock()
    start = time.time()

    #q.put("rsouza/MMD")
    for i in data:
        if check_files(platform,i):
            q.put(i)
    p = MyPool(3)
    #multiprocessing.cpu_count()
    for i in range(3):
        p.apply_async(sha_filter_p, args=(lock, q, platform,))
    p.close()
    p.join()
    end = time.time()
    print(end-start)
    print("All Done")
    #check_err_folder()


def check_err_folder():
    if sys.platform == "darwin":
        platform = apple
        url = "/Volumes/SL-E1/2019_Summer_Project/filter_notebooks.csv"
    else:
        platform = ubuntu
        url = "/media/lofowl/SL-E1/2019_Summer_Project/filter_notebooks.csv"
    lists = os.listdir(platform)
    for i in lists:
        switch = i.split("#")
        save_to = platform+i+"/"
        repo = save_to+switch[-1]
        if os.path.exists(repo):
            print(platform+i)
            os.system("rm -rf "+platform+i)
        elif os.path.exists(platform+i):
            if len(os.listdir(platform+i)) == 0:
                print(platform+i)
                os.system("rm -rf "+platform+i)

def main(name):
    print(name)
    switch = name.split("/")
    switch_name = name.replace("/","#")
    save_to = ubuntu+switch_name+"/"
    repo = save_to+switch[-1]
    path = save_to
    file = repo

    repos = git.Repo.init(path=repo)

    stat = repos.git.log("*.ipynb",all=True,full_history=True,no_merges=True,follow=True,pretty="%H")
    stat = stat.split("\n")
    stat = list(set(stat))


    if len(stat) >= 50:
        N = 5
        stat_list = np.array_split(stat,N)
    else:
        N = 1
        stat_list = [stat]

    start = time.time()
    statinfo = os.stat(file)
    print(statinfo.st_size)


    end = time.time()
    download_time = end - start


    repos_list = []
    path_list = []
    files_name = os.listdir(path)
    print(files_name)
    for i in files_name:
        print(i)
        if switch[1] in i:
            new_path = path +i
            repos_list.append(git.Repo.init(path=new_path))
            path_list.append(new_path)

    input = list(zip(repos_list,stat_list,path_list))
    start = time.time()
    final_list = []
    with concurrent.futures.ProcessPoolExecutor(max_workers=N) as executor:
        files_list = list(executor.map(sub_run,input))

    final_list = []
    for i in files_list:
        if len(i) != 0:
            final_list += i


    columns_name = ["sha",
                    "status",
                    "parent_index",
                    "child_index",
                    "file",
                    "types"]
    pa = pd.DataFrame(final_list,columns=columns_name)
    pa.to_csv(save_to+"change.csv",index=0)
    end = time.time()
    runtime = end - start
    finaltime = download_time + runtime

    for i in path_list:
        os.system("rm -rf "+i)

def redo_exits_folder():
    path = "/media/lofowl/SL-E1/2019_Summer_Project/repo4/"
    list_name = os.listdir(path)
    new_list_name = [i.split("#") for i in list_name ]
    repo_name_list = list(map(lambda x:(path+x[0]+"#"+x[1]+"/"+x[1],x[0]+"/"+x[1]), new_list_name))
    count = 0
    final_name_list = []
    for i in repo_name_list:
        if os.path.exists(i[0]):
            final_name_list.append(i)

    print(len(final_name_list))
    for i in final_name_list:
        try:
            main(i[1])
        except:
            pass

if __name__ == "__main__":
    multi_processing()
