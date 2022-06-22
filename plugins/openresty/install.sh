#!/bin/bash
PATH=/bin:/sbin:/usr/bin:/usr/sbin:/usr/local/bin:/usr/local/sbin:~/bin
export PATH

curPath=`pwd`
rootPath=$(dirname "$curPath")
rootPath=$(dirname "$rootPath")
serverPath=$(dirname "$rootPath")


action=$1
type=$2

VERSION=$2
install_tmp=${rootPath}/tmp/mw_install.pl
openrestyDir=${serverPath}/source/openresty

if id www &> /dev/null ;then 
    echo "www UID is `id -u www`"
    echo "www Shell is `grep "^www:" /etc/passwd |cut -d':' -f7 `"
else
    groupadd www
	# useradd -g www -s /sbin/nologin www
	useradd -g www -s /bin/bash www
fi

# cd /www/server/mdserver-web/plugins/openresty && /bin/bash install.sh install 1.21.4.1
Install_openresty()
{
	mkdir -p ${openrestyDir}
	echo '正在安装脚本文件...' > $install_tmp

	cd $serverPath/mdserver-web/plugins/php/lib && /bin/bash zlib.sh

	if [ ! -f ${openrestyDir}/openresty-${VERSION}.tar.gz ];then
		wget -O ${openrestyDir}/openresty-${VERSION}.tar.gz https://openresty.org/download/openresty-${VERSION}.tar.gz
	fi


	cd ${openrestyDir} && tar -zxvf openresty-${VERSION}.tar.gz

	# --with-openssl=$serverPath/source/lib/openssl-1.0.2q
	cd ${openrestyDir}/openresty-${VERSION} && ./configure --prefix=$serverPath/openresty \
	--with-http_v2_module \
	--with-http_ssl_module  \
	--with-http_slice_module \
	--with-http_stub_status_module \
	--with-zlib=$serverPath/lib/zlib

	make && make install && make clean
	echo "${VERSION}" > $serverPath/openresty/version.pl

	if [ -d $serverPath/openresty/nginx/conf ];then
		echo "" > $serverPath/openresty/nginx/conf/enable-php-00.conf
	fi
	echo '安装完成' > $install_tmp
}

Uninstall_openresty()
{
	rm -rf $serverPath/openresty
	
	if [ -f /lib/systemd/system/openresty.service ];then
		rm -rf /lib/systemd/system/openresty.service
	fi
	echo '卸载完成' > $install_tmp
}

action=$1
if [ "${1}" == 'install' ];then
	Install_openresty
else
	Uninstall_openresty
fi
