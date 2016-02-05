# -*- mode: ruby -*-
# vi: set ft=ruby :

$script = <<SCRIPT
# We need FreeCAD 0.15 for Draft-dxf-importer 1.38 but Ubuntu 14.04/trusty
# only ships with FreeCAD 0.13.
#sudo add-apt-repository --yes ppa:freecad-maintainers/freecad-stable
sudo add-apt-repository --yes ppa:freecad-maintainers/freecad-daily
sudo apt-get update
sudo apt-get --yes install freecad

# Grab the kb_builder source code and get things ready to run.
sudo apt-get --yes install git
sudo git clone --branch master --single-branch --depth 1 \
  http://github.com/swill/kb_builder.git /home/vagrant/kb_builder
sudo apt-get --yes install build-essential python-dev python-pip
sudo pip install --requirement /home/vagrant/kb_builder/requirements.txt

# Fetch the Draft-dxf-importer.
sudo git clone --branch 1.38 --single-branch --depth 1 \
  https://github.com/yorikvanhavre/Draft-dxf-importer /root/.FreeCAD
SCRIPT

Vagrant.configure(2) do |config|
  config.vm.box = "ubuntu/trusty64"

  config.vm.network "forwarded_port", guest: 80, host: 8080

  config.vm.synced_folder ".", "/vagrant", disabled: true

  #config.vm.provider "virtualbox" do |vb|
  #  vb.memory = "1024"
  #end

  config.vm.provision "shell", inline: $script
end
