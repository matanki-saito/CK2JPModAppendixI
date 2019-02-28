#!/usr/bin/env python
# -*- coding:utf-8 -*-

import json
import os
import shutil
import urllib.request
import zipfile
from datetime import datetime as dt
from os.path import join

from boto3.session import Session

_ = join


def download_trans_zip_from_paratranz(project_id,
                                      secret,
                                      base_url="https://paratranz.cn",
                                      save_file_path="./tmp/paratranz.zip"):
    """
    paratranzからzipをダウンロードする
    :param project_id:
    :param secret:
    :param base_url:
    :param save_file_path:
    :return:
    """

    request_url = "{}/api/projects/{}/artifacts/download".format(base_url, project_id)
    req = urllib.request.Request(request_url)
    req.add_header("Authorization", secret)

    with open(save_file_path, "wb") as my_file:
        my_file.write(urllib.request.urlopen(req).read())


def download_asset_from_github(repository_author,
                               repository_name,
                               release_tag=None,
                               file_name=None,
                               save_file_path="./tmp/font.zip"):
    """
    githubからアセットをダウンロード。未指定の場合は最新を取得
    :param repository_author:
    :param repository_name:
    :param release_tag:
    :param file_name:
    :param save_file_path:
    :return:
    """
    api_base_url = "https://api.github.com/repos/{}/{}".format(repository_author, repository_name)

    if release_tag is None:
        response = urllib.request.urlopen("{}/releases/latest".format(api_base_url))
        content = json.loads(response.read().decode('utf8'))
        release_tag = content["tag_name"]

    if file_name is None:
        response = urllib.request.urlopen("{}/releases/tags/{}".format(api_base_url, release_tag))
        content = json.loads(response.read().decode('utf8'))
        file_name = content["assets"][0]["name"]

    request_url = "{}/{}/{}/releases/download/{}/{}".format("https://github.com",
                                                            repository_author,
                                                            repository_name,
                                                            release_tag,
                                                            file_name
                                                            )
    req = urllib.request.Request(request_url)

    with open(save_file_path, "wb") as my_file:
        my_file.write(urllib.request.urlopen(req).read())


def assembly_core_mod(font_asset_zip_path="./tmp/font.zip",
                      paratranz_trans_zip_path="./tmp/paratranz.zip",
                      core_folder_path="./out/CORE"):
    """
    コアモッドを作成
    :param font_asset_zip_path:
    :param paratranz_trans_zip_path:
    :param core_folder_path:
    :return:
    """

    # 出力フォルダをクリア
    shutil.rmtree(core_folder_path, ignore_errors=True)

    # shutilでの移動は、移動先ディレクトリがなくても自動で作成されるが、
    # "正しく"動作しないので、予め作成しておく必要がある
    # 具体的に言うと、構造が正しく保持されずに移動される
    # 出力フォルダを作成する
    os.makedirs(core_folder_path, exist_ok=True)

    # 画像ファイル
    shutil.copy(_(".", "resource", "title.jpg"), core_folder_path)

    # interface
    shutil.copytree(_(".", "resource", "interface"), _(core_folder_path, "interface"))

    # gfx
    # フォント側を調整する必要がある。
    def filter_f(item):
        if item.startswith("aoyagireisyo60-aoyagi") or \
                item.startswith("aoyagireisyo60-appb") or \
                item.startswith("tuikafont1"):
            return False
        else:
            return True

    salvage_files_from_github_font_zip(out_dir_path=_(core_folder_path, "gfx", "fonts"),
                                       filter_f=filter_f,
                                       resource_path=font_asset_zip_path)

    # localisation
    salvage_files_from_paratranz_trans_zip(copy_dir_path=_(core_folder_path, "localisation"),
                                           folder_list=["localisation"],
                                           paratranz_zip_path=paratranz_trans_zip_path)

    # zip化する
    return shutil.make_archive(core_folder_path, 'zip', root_dir=core_folder_path)


def salvage_files_from_github_font_zip(out_dir_path, filter_f, resource_path="./tmp/font.zip"):
    with zipfile.ZipFile(resource_path) as font_zip:
        special_files = filter(filter_f, font_zip.namelist())

        font_zip.extractall(path=out_dir_path, members=special_files)


def salvage_files_from_paratranz_trans_zip(copy_dir_path, paratranz_zip_path="./tmp/paratranz.zip",
                                           folder_list=[]):
    with zipfile.ZipFile(paratranz_zip_path) as paratranz_zip:
        special_files = filter(lambda name: name.startswith("special/"), paratranz_zip.namelist())

        paratranz_zip.extractall(path=_(".", "tmp", "trans"), members=special_files)

    for folder in folder_list:
        shutil.copytree(_(".", "tmp", "trans", "special", folder), copy_dir_path)


def upload_mod_to_s3(upload_file_path,
                     name,
                     bucket_name,
                     access_key,
                     secret_access_key,
                     region):
    session = Session(aws_access_key_id=access_key,
                      aws_secret_access_key=secret_access_key,
                      region_name=region)

    s3 = session.resource('s3')
    s3.Bucket(bucket_name).upload_file(upload_file_path, name)


def main():
    # 一時フォルダ用意
    os.makedirs(_(".", "tmp"), exist_ok=True)
    os.makedirs(_(".", "out"), exist_ok=True)

    # フォントセットの最新版をダウンロードする
    download_asset_from_github(repository_author="matanki-saito", repository_name="CK2Fontcreate")

    # 翻訳の最新版をダウンロードする
    download_trans_zip_from_paratranz(project_id=91, secret=os.environ.get("PARATRANZ_SECRET"))

    # コアModを構築する
    core_mod_zip_path = assembly_core_mod()

    # S3にアップロード
    upload_mod_to_s3(upload_file_path=core_mod_zip_path,
                     name=dt.now().strftime('%Y-%m-%d_%H-%M-%S-{}'.format("ck2-core")),
                     bucket_name="triela-file",
                     access_key=os.environ.get("AWS_S3_ACCESS_KEY"),
                     secret_access_key=os.environ.get("AWS_S3_SECRET_ACCESS_KEY"),
                     region="ap-northeast-1")


if __name__ == "__main__":
    main()
