#!/usr/bin/env python3
import datetime
import hashlib
import json
import os
import sys
import urllib.error
import urllib.request

try:
    from lxml import etree
    USE_LXML = True
except ImportError:
    import xml.etree.ElementTree as etree
    USE_LXML = False

USER_NAME = os.environ.get('USER_NAME', 'HARDIK-31')
TOKEN = os.environ.get('ACCESS_TOKEN') or os.environ.get('GITHUB_TOKEN') or ''
GRAPHQL_URL = 'https://api.github.com/graphql'
ACCOUNT_START = datetime.datetime(2020, 6, 18)


def query_graphql(query, variables=None):
    if not TOKEN:
        raise ValueError("GitHub ACCESS_TOKEN or GITHUB_TOKEN not set")
    payload = json.dumps({'query': query, 'variables': variables or {}}).encode('utf-8')
    req = urllib.request.Request(
        GRAPHQL_URL,
        data=payload,
        headers={
            'Authorization': f'token {TOKEN}',
            'Content-Type': 'application/json',
            'User-Agent': 'github-profile-neofetch'
        }
    )
    with urllib.request.urlopen(req) as resp:
        return json.loads(resp.read().decode('utf-8'))


def calculate_uptime(start_date):
    today = datetime.datetime.today()
    years = today.year - start_date.year
    months = today.month - start_date.month
    if today.day < start_date.day:
        months -= 1
    if months < 0:
        years -= 1
        months += 12
    y_str = f"{years} year" + ("s" if years != 1 else "")
    m_str = f"{months} month" + ("s" if months != 1 else "")
    return f"{y_str}, {m_str} (since 2020)"


def find_and_replace(root, element_id, new_text):
    for elem in root.iter():
        if elem.get('id') == element_id:
            elem.text = str(new_text) if new_text is not None else ''
            return


def justify_format(root, element_id, new_text, target_length=0):
    if isinstance(new_text, int):
        val_str = f"{new_text:,}"
    else:
        val_str = str(new_text)
    find_and_replace(root, element_id, val_str)

    if target_length > 0:
        rem = max(0, target_length - len(val_str))
        if rem <= 1:
            dot_str = ' '
        elif rem == 2:
            dot_str = ' . '
        else:
            dot_str = ' ' + ('.' * rem) + ' '
        find_and_replace(root, f"{element_id}_dots", dot_str)


def update_svg(filename, uptime_str, repo_count, contrib_count, star_count, commit_str, follower_count, loc_total, loc_add, loc_del):
    if not USE_LXML:
        etree.register_namespace('', 'http://www.w3.org/2000/svg')

    tree = etree.parse(filename)
    root = tree.getroot()

    find_and_replace(root, 'age_data', uptime_str)
    justify_format(root, 'repo_data', repo_count, 6)
    justify_format(root, 'contrib_data', contrib_count)
    justify_format(root, 'star_data', star_count, 14)
    justify_format(root, 'commit_data', commit_str, 22)
    justify_format(root, 'follower_data', follower_count, 10)
    justify_format(root, 'loc_data', loc_total, 9)
    justify_format(root, 'loc_add', loc_add)
    justify_format(root, 'loc_del', loc_del, 7)

    tree.write(filename, encoding='utf-8', xml_declaration=True)
    print(f"Updated {filename} successfully.")


def fetch_stats():
    query = '''
    query($login: String!) {
      user(login: $login) {
        id
        createdAt
        followers {
          totalCount
        }
        ownedRepos: repositories(first: 100, ownerAffiliations: [OWNER]) {
          totalCount
          nodes {
            stargazers {
              totalCount
            }
          }
        }
        allRepos: repositories(first: 100, ownerAffiliations: [OWNER, COLLABORATOR, ORGANIZATION_MEMBER]) {
          totalCount
        }
        contributionsCollection {
          contributionCalendar {
            totalContributions
          }
        }
      }
    }
    '''
    res = query_graphql(query, {'login': USER_NAME})
    user = res['data']['user']
    user_id = user['id']
    created_at = user['createdAt']
    followers = user['followers']['totalCount']
    repos_owned = user['ownedRepos']['totalCount']
    repos_contrib = user['allRepos']['totalCount']
    stars = sum(node['stargazers']['totalCount'] for node in user['ownedRepos']['nodes'])
    yearly_commits = user['contributionsCollection']['contributionCalendar']['totalContributions']
    return {
        'id': user_id,
        'createdAt': created_at,
        'followers': followers,
        'repos_owned': repos_owned,
        'repos_contrib': repos_contrib,
        'stars': stars,
        'yearly_commits': yearly_commits
    }


def main():
    print(f"Synchronizing profile stats for {USER_NAME}...")
    uptime_str = calculate_uptime(ACCOUNT_START)

    commit_str = "2,500+"
    loc_total = "320,000+"
    loc_add = "380,000+"
    loc_del = "60,000+"
    repos = 60
    contribs = 68
    stars = 6
    followers = 2

    if TOKEN:
        try:
            stats = fetch_stats()
            repos = stats['repos_owned']
            contribs = max(stats['repos_contrib'], repos)
            stars = stats['stars']
            followers = stats['followers']
            if stats['yearly_commits'] > 0:
                commit_str = f"{stats['yearly_commits'] + 1500:,}"
            print(f"Stats fetched: {repos} repos, {stars} stars, {followers} followers, {contribs} contributed")
        except Exception as e:
            print(f"GraphQL fetch failed: {e}. Using cached/fallback stats.")
    else:
        print("No GitHub token supplied; using default values.")

    for svg_file in ['dark_mode.svg', 'light_mode.svg']:
        if os.path.exists(svg_file):
            update_svg(svg_file, uptime_str, repos, contribs, stars, commit_str, followers, loc_total, loc_add, loc_del)


if __name__ == '__main__':
    main()
