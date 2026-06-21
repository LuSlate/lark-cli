module.exports = function (callback) {
  callback({
    name: 'lark-cli-openapi-ppe-pure-svg',
    groupName: 'lark-cli',
    rules: [
      '/^https:\\/\\/open\\.feishu\\.cn\\/(.*)$/ https://open.feishu-pre.cn/$1',
      'https://open.feishu.cn/ reqHeaders://Env=Pre_release',
      'https://open.feishu.cn/ reqHeaders://x-tt-env=ppe_pure_svg',
      'https://open.feishu-pre.cn/ reqHeaders://Env=Pre_release',
      'https://open.feishu-pre.cn/ reqHeaders://x-tt-env=ppe_pure_svg',
      '/^https:\\/\\/accounts\\.feishu\\.cn\\/(.*)$/ https://accounts.feishu-pre.cn/$1',
    ].join('\n'),
  });
};
