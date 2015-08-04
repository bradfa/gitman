#! /usr/bin/env python3

import json, textwrap, argparse, shutil, os, subprocess, sys, git

class GitmanRepo():

	def __init__(self, project, json_obj):

		self.data = json_obj
		self.project = project
		self.parse(self.data)
		self.repo = None

		if os.path.isdir(self.path):
			self.repo = git.Repo(self.path)

	def parse(self, data):

		self.name = self.data['name']
		self.remote = self.data['remote']
		self.branch = self.data['branch']
		self.commit = self.data['commit']
		self.path = self.data['path']
		self.address = self.data['address']

	def sync(self):

		print("Syncing {}".format(self.name))

		gitman_remote = self.project.find_remote(self.remote)

		if self.repo is None:

			print("Cloning...")
			self.repo = git.Repo.clone_from("{}/{}".format(gitman_remote.fetch, self.address), self.path, origin=self.remote)
			print("Checking out {}".format(self.branch))
			self.repo.git.checkout(self.branch)

			if (self.commit.upper() != "HEAD"):
				self.repo.head.reset(self.commit)

			return

		remote = self.repo.remote(self.remote)

		if not remote:
			print("Remote '{}' not found, adding".format(self.remote))
			remote = git.Remote.add(self.repo, self.remote, "{}/{}".format(gitman_remote.fetch, self.address))

		print("Fetching {}".format(remote))
		remote.fetch()

		ahead = False

		commits_ahead = self.repo.iter_commits('{0}..{1}/{0}'.format(self.branch, self.remote))

		for commit in commits_ahead:
			ahead = True
			break

		if (ahead):
			print("Repo ahead of remote, please push or branch changes before syncing")

		if not self.repo.is_dirty():

			if (self.commit.upper() == "HEAD"):
				print("Pulling...")
				remote.pull()
			else:
				print("Resetting...")
				self.repo.head.reset(self.commit, True, True)

		else:

			print("Dirty repo, please fix before syncing")

		return

	def __str__(self):

		printstr = ""

		printstr += "Name: {}\n".format(self.name)
		printstr += "Remote: {}\n".format(self.remote)
		printstr += "Branch: {}\n".format(self.branch)
		printstr += "Commit: {}\n".format(self.commit)
		printstr += "Path: {}\n".format(self.path)
		printstr += "Address: {}\n".format(self.address)

		return printstr

class Remote:

	def __init__(self, json_obj):

		self.data = json_obj
		self.parse(self.data)

	def parse(self, data):

		self.name = self.data['name']
		self.fetch = self.data['fetch']

	def __str__(self):

		printstr = ""

		printstr += "Name: {}\n".format(self.name)
		printstr += "Fetch: {}\n".format(self.fetch)

		return printstr

class Project:

	def __init__(self, json_obj):

		self.data = json_obj
		self.remotes = []
		self.repos = []

		for item in self.data:

			if item == "repos":
				for repo in self.data[item]:
					self.repos.append(GitmanRepo(self, repo))
				continue

			if item == "remotes":
				for remote in self.data[item]:
					self.remotes.append(Remote(remote))
				continue

		print("Remotes: {}".format(len(self.remotes)))
		print("Repos: {}".format(len(self.repos)))

	def sync(self):

		for repo in self.repos:

			try:
				repo.sync()
			except:
				raise

	def find_remote(self, name):

		for remote in self.remotes:

			if remote.name == name:

				return remote

		return None

	def __str__(self):

		printstr = ""

		printstr += "Project: {}\n".format(self.data['name']) + "\n"

		printstr += "  Repos:\n\n"

		for repo in self.repos:
			printstr += textwrap.indent(repo.__str__(), '    ')
			printstr += "\n"

		printstr += "  Remotes:\n\n"

		for remote in self.remotes:
			printstr += textwrap.indent(remote.__str__(), '    ')
			printstr += "\n"

		return printstr

parser = argparse.ArgumentParser()

parser.add_argument("--init", help="Initialise a gitman tree", nargs="+", metavar=('gitsrc','path'))
parser.add_argument("--sync", help="Updates and syncs your git trees inline with the upstream manifest", nargs="*", metavar=('commit/tag'))
parser.add_argument("--info", help="Print info about the current project", action="store_true")
parser.add_argument("--project", help="Only apply the command to a specific project", nargs=1)

args = parser.parse_args()

prefix_dir = ""

if args.init:

	try:
			if args.init[1]:
				prefix_dir = args.init[1] + "/"

			try:
				os.makedir(prefix_dir)
			except:
				pass

			try:
				os.makedirs(prefix_dir+".gitman")
			except:
				print("Gitman tree already present in directory")
				print("Exiting....")
				sys.exit(1)

			git.Repo.clone_from(args.init[0], "{}/.gitman/manifest.git".format(prefix_dir))

	except:

		print("Git error")

		shutil.rmtree(prefix_dir+".gitman")

		if args.init[0]:
			try:
				os.rmdir(args.init[0])
			except:
				pass

		print("Exiting...")
		sys.exit(1)

if args.sync is not None:

	print("Syncing")

	try:
		if args.sync:
			sync_cmd = 'git reset --hard {}'.format(args.sync[0])
		else:
			sync_cmd = 'git merge --ff-only'

		output = subprocess.check_output(
			'cd .gitman/manifest.git && git fetch && {}'.format(sync_cmd),
				shell=True,
				stderr=subprocess.STDOUT)

	except subprocess.CalledProcessError as e:
		print ("Git error:")
		sys.stdout.buffer.write(e.output)
		sys.exit(1)

	sys.stdout.buffer.write(output)

try:
	manifest_file = open(prefix_dir+".gitman/manifest.git/manifest.json")
except:
	print("Not in a gitman directory")
	sys.exit(1)

projects = []

manifest = json.load(manifest_file)

for item in manifest:

	if item == "projects":

		for	project in manifest[item]:

			if args.project is None or args.project[0] == project['name']:
				projects.append(Project(project))

if args.sync is not None:

	for project in projects:
		project.sync()

if args.info:

	for project in projects:
		print(project)
