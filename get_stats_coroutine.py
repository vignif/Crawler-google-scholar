"""this script crawls for the statistics of researchers in google scholar
    and save them in a file called: co_data.txt
    the source information must be an .xlsx file with two columns [surname, name]
    per each researcher provided in the file it gets
    [tot # citations; h-index; i10_index; fields_of_research; #citations last 5 years]
    the crawler exploit the informations via the description of the tags in the html of google scholar

    be aware that too many requests to a server might interrupt your script, please
    set a proper sleep timing

    debug mode is also available for crawl local hosted websites.
    """

import aiohttp
import asyncio
import bs4
import re
from pandas import read_excel
import time


debug = False

my_sheet = 'Tabellenblatt1'
file_name = 'Research Statistics.xlsx' # name of your excel file

df = read_excel(file_name, sheet_name = my_sheet)


def enable_debug_mode(debug_bool):
    if debug_bool == True:
        web_site = 'http://127.0.0.1:5000'
        base_url="http://127.0.0.1:5000/"
        to_cut=len(base_url)
    else:
        web_site = 'https://scholar.google.com'
        base_url="https://scholar.google.com/citations?hl=it&view_op=search_authors&mauthors="
        to_cut=len(base_url)
    return web_site, base_url, to_cut

web_site, base_url, to_cut=enable_debug_mode(debug)

def init_file():
    f=open("co_data.txt","a")
    #create base columns Names
    template=open('template.txt','r')
    f.write(template.read())
    return f

def close_file(f):
    print("File saved! \n")
    f.close()

async def get_name(url):
    name=url[to_cut:]
    return name

def split_name(name):
    temp_name_list=name.split('+')
    name=temp_name_list[0]
    surname=temp_name_list[1]
    return name, surname

async def save_in_file(f, name, Data):
    #print("name: ",name)
    name, surname = split_name(name)
    # print("saving: " + name + " " + surname)
    f.write(name + "; " + surname + "; ")
    f.write(Data[0] + "; " + Data[1] + "; " + Data[2] + "; ")
    for i in Data[3]:
        f.write(i + ", ")
    f.write("; " + Data[4] + "; " + Data[5] + "; " + Data[6] + " ;" + Data[7]+ "; " + Data[8] + "; " + Data[9] + "\n")

async def find_and_extract_data(soup):
    # print("find_and_extract_data")
    central_table=soup.find(id="gsc_prf_w")
    description=central_table.find("div", {'class':"gsc_prf_il"}).text
    fields=[]
    for field in central_table.find("div", {'class':"gsc_prf_il", 'id':'gsc_prf_int'}).contents:
        if isinstance(field, bs4.element.NavigableString):
            continue
        if isinstance(field, bs4.element.Tag):
            fields.append(field.text)
    corner_table = soup.find("div",{"class":"gsc_rsb_s gsc_prf_pnl"})
    try:
        num_cit_index=list(corner_table.find_all("td", {"class":"gsc_rsb_std"}))
        hist=corner_table.find("div",{"class":"gsc_md_hist_b"}).contents
    except:
        raise ValueError

    for i in range(len(hist)):
        if isinstance(hist[i], bs4.element.Tag):
            hist.append(hist[i])
	##take stats all time index [0] , [2] , [4]
	##take stats last 5 years index [1], [3], [5]

    num_cit  = num_cit_index[0].text #all time
    h_index  = num_cit_index[2].text
    i10_index= num_cit_index[4].text
    n14 = hist[-6].text #year-5
    n15 = hist[-5].text #year-4
    n16 = hist[-4].text #year-3
    n17 = hist[-3].text #year-2
    n18 = hist[-2].text #last_year
    n19 = hist[-1].text #current_year
    Data = [num_cit, h_index, i10_index, fields, n14, n15, n16, n17, n18, n19]
    return Data


async def store_in_list(L, name, Data):
    name, surname = split_name(name)
    L.append([surname, name, Data])
    return L

def data_not_available(file, name):
    name, surname = split_name(name)
    file.write("Data not available for " + name + " " + surname + "\n")

async def fetch_all(url,f):
    # connect to the server
    async with aiohttp.ClientSession() as session:
        # create get request
        async with session.get(url) as response:
            name= await get_name(url)
            response = await response.text()
            soup=bs4.BeautifulSoup(response, 'html.parser')
            result=soup.find("h3",{'class':'gs_ai_name'}) #find name and its url
            if result is None:
                data_not_available(f, name)
            else:
                link= result.find('a', href = re.compile(r'[/]([a-z]|[A-Z])\w+')).attrs['href']
                L=[]
                #create sub get request
                async with session.get(web_site+link) as subresponse:
                    #print("start: " + name)
                    print("request: " + name +" with status: "+str(subresponse.status))
                    html = await subresponse.text()
                    soup = bs4.BeautifulSoup(html, 'html.parser')
                    Data = await find_and_extract_data(soup)
                    #print(await get_name(web_site+link))
                    a = await store_in_list(L, name, Data)
                    await save_in_file(f, name, Data)


def cut(L,n):
    'takes a list [L] and crop the first n elements'
    if n=0:
        n=len(L)
    return L[:n]


def create_links(n):
    # base_url="https://scholar.google.com/citations?hl=it&view_op=search_authors&mauthors="
    all=[]
    for i in range(len(df)):
        name = df.iloc[i][1]
        surname = df.iloc[i][0]
        if isinstance(name, str):
            all.append(base_url+name+"+"+surname)
        else:
            break
    all=cut(all,n)
    return all

def print_all_pages(n):
    f=init_file()
    pages = create_links(n)
    #print(pages)
    tasks =  []
    loop = asyncio.new_event_loop()
    for page in pages:
        tasks.append(loop.create_task(fetch_all(page,f)))

    loop.run_until_complete(asyncio.wait(tasks))
    loop.close()
    close_file(f)

def main():
    n=0 #check for all the names in the file_name
        #set n to crawl only the first [n] rows of your researcher file_name
    print_all_pages(n)

if __name__ == "__main__":
    main()
