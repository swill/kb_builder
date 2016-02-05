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

  # Create a forwarded port mapping which allows access to a specific port
  # within the machine from a port on the host machine. In the example below,
  # accessing "localhost:8080" will access port 80 on the guest machine.
  # config.vm.network "forwarded_port", guest: 80, host: 8080

  # Create a private network, which allows host-only access to the machine
  # using a specific IP.
  # config.vm.network "private_network", ip: "192.168.33.10"

  # Create a public network, which generally matched to bridged network.
  # Bridged networks make the machine appear as another physical device on
  # your network.
  # config.vm.network "public_network"

  config.vm.synced_folder ".", "/vagrant", disabled: true

  #config.vm.provider "virtualbox" do |vb|
  #  vb.memory = "1024"
  #end

  config.vm.provision "shell", inline: $script
end
