import os
import re
import requests
import itertools
import heapq
import logging
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger()
logger.setLevel(logging.NOTSET)

console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)
console_handler_format = '%(asctime)s | %(levelname)s: %(message)s'
console_handler.setFormatter(logging.Formatter(console_handler_format))
logger.addHandler(console_handler)

repo = os.environ["REPOS"].split(",")
auth = (os.environ["NEXUS_USER"], os.environ["NEXUS_PASSWORD"])
base_url = 'https://' + os.environ["NEXUS_DOMAIN"] + '/service/rest/v1/components'

all_count = int(os.environ["ALL_COUNT"])
nuget_release_count = int(os.environ["NUGET_RELEASE_COUNT"])
nuget_count = int(os.environ["NUGET_COUNT"])
zhp_old = int(os.environ["##_OLD"])
zhp_new = int(os.environ["##_NEW"])

# Для запуска удаления в .env изменить значение READY_TO_DEL на True
rtd = os.environ["READY_TO_DEL"]

def getImages(url, repo):
  params = {'repository': repo}
  images = []
  while True:
    response = requests.get(url, auth=(auth[0],auth[1]), params=params)
    response = response.json()
    for image in response['items']:
      imageName = image['name']
      imageVersion = image['version']
      imageID = image['id']
      imageFormat = {
        "id" : imageID,
        "name" : imageName,
        "version" : imageVersion
        }
      images.append(imageFormat)
    continuationToken = response['continuationToken']
    if continuationToken is None:
      break
    cToken = {"continuationToken": response["continuationToken"]}
    continuationToken = cToken['continuationToken']
    params['continuationToken'] = continuationToken
  return images

def getId(id):
  return id["id"]
def getVersion(version):
  return version["version"]
def getIntVersion(intversion):
  return intversion["intversion"]

def deleteList(url, repo):
  versionsToDel = []
  images = getImages(url, repo)
  images.sort(key=lambda image: image['name'])
  imagesList = itertools.groupby(images, lambda image: image['name'])

  # Политика удаления для всех образов
  if repo != "nuget-##":
    for name, group in imagesList:
      versions = []
      versions_zhp_old = []
      versions_zhp_new = []
      for i in group:
        version = i['version']
        id = i['id']
        name = i['name']
        result = re.search(r'\D', version[0])
        if result == None:
          v = re.sub(r'\D', '', version)
          ve = int(v)
          ver = {
            "id" : id,
            "name" : name,
            "version" : version,
            "intversion" : ve
          }
          # Все компоненты, кроме ##
          if name != "##/##/##" \
            and name != "##/##/##" \
            and name != "##/##/##" \
            and name != "##/##/##":
            versions.append(ver)
          # ##
          else:
            # Старая ##
            if version[0] == "4":
              versions_zhp_old.append(ver)
            # Новая ##
            if version[0] == "5":
              versions_zhp_new.append(ver)
      # Все компоненты, кроме ##
      versionsLarg = heapq.nlargest(all_count, versions, key=getIntVersion)
      for a in versions:
        vers = int(a["intversion"])
        versionSmall = versionsLarg[-1]
        versi = int(versionSmall["intversion"])
        if vers < versi:
          versionsToDel.append(a)
      # Старая ##
      versionsLarg = heapq.nlargest(zhp_old, versions_zhp_old, key=getIntVersion)
      for a in versions_zhp_old:
        vers = int(a["intversion"])
        versionSmall = versionsLarg[-1]
        versi = int(versionSmall["intversion"])
        if vers < versi:
          versionsToDel.append(a)
      # Новая ##
      versionsLarg = heapq.nlargest(zhp_new, versions_zhp_new, key=getIntVersion)
      for a in versions_zhp_new:
        vers = int(a["intversion"])
        versionSmall = versionsLarg[-1]
        versi = int(versionSmall["intversion"])
        if vers < versi:
          versionsToDel.append(a)

  # Политика удаленния для репозиторя nuget
  else:
    for name, group in imagesList:
      versions = []
      for i in group:
        version = i['version']
        id = i['id']
        name = i['name']
        result = re.search(r'[a-zA-Z]', version)
        v = re.sub(r'\D', '', version)
        ve = int(v)
        ver = {
          "id" : id,
          "name" : name,
          "version" : version,
          "intversion" : ve
        }
        versions.append(ver)
      # Нугеты только с цифрами
      if result == None:
        versionsLarg = heapq.nlargest(nuget_release_count, versions, key=getIntVersion)
        for a in versions:
          vers = int(a["intversion"])
          versionSmall = versionsLarg[-1]
          versi = int(versionSmall["intversion"])
          if vers < versi:
            versionsToDel.append(a)
      # Все остальные нугеты
      else:
        versionsLarg = heapq.nlargest(nuget_count, versions, key=getIntVersion)
        for a in versions:
          vers = int(a["intversion"])
          versionSmall = versionsLarg[-1]
          versi = int(versionSmall["intversion"])
          if vers < versi:
            versionsToDel.append(a)

  logger.warning("Компоненты на удаление: ")

  for log in versionsToDel:
    _i = log['id']
    _n = log['name']
    _v = log['version']
    component = {
      # "id" : _i,
      "name" : _n,
      "version" : _v
    }
    logger.info(component)
  return versionsToDel

def deleteComponents(url, repo):
  ids = deleteList(url, repo)
  for id in ids:
    idsToDel = id["id"]
    urlToDel = url + '/' + idsToDel
    requests.delete(urlToDel, auth=(auth[0],auth[1]))

def main(url, repo):
  if rtd == "True":
    logger.warning("УДАЛЕНИЕ ЗАПУЩЕНО!!! Для отключения удаления в .env изменить значение READY_TO_DEL на False")
    for r in repo:
      deleteComponents(url, r)
    logger.warning("Компоненты удалены!!!")
  else:
    logger.warning("Удаление не включено. Для запуска удаления в .env изменить значение READY_TO_DEL на True")
    for r in repo:
      deleteList(url, r)
    logger.warning("Удаление не включено. Для запуска удаления в .env изменить значение READY_TO_DEL на True")


main(base_url, repo)
