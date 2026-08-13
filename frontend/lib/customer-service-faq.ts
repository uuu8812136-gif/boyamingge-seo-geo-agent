import { SITE } from '@/lib/site';

export type CustomerServiceFaqAnswer = {
  answer: string;
  intent: string;
  handoff: boolean;
  source: 'faq';
};

export const CUSTOMER_SERVICE_QUICK_QUESTIONS = [
  '上门测量收费吗？',
  '阳台封窗怎么报价？',
  '旧窗改造多久能装？',
  '隔音窗怎么选？',
  '断桥铝怎么选？',
  '漏水怎么处理？',
  '质保多久？',
  '转人工',
];

export const CUSTOMER_SERVICE_HANDOFF_REPLY = `可以，已经为你切换人工咨询入口。你可以直接拨打 ${SITE.hotlineDisplay}，或留下姓名、城市、需求和手机号，工作人员会按顺序回访。`;

const FAQ_RULES: Array<{ pattern: RegExp; answer: string; intent: string; handoff?: boolean }> = [
  {
    pattern: /人工|转人工|真人|客服|电话|联系|回电|销售|顾问/,
    intent: 'handoff',
    handoff: true,
    answer: CUSTOMER_SERVICE_HANDOFF_REPLY,
  },
  {
    pattern: /预约|留资|怎么约|怎么预约|报名|下单|安排/,
    intent: 'booking',
    answer: `你可以直接在页面填写预约测量表单，也可以拨打 ${SITE.hotlineDisplay}。建议留下城市、小区、楼层、需求和手机号，门店会先电话确认，再安排师傅上门。`,
  },
  {
    pattern: /收费|免费|测量|上门|量尺|量房/,
    intent: 'measurement',
    answer: '多数城市门店支持预约上门测量。是否收费会根据城市、距离和现场条件确认；测量时会记录洞口尺寸、楼层、开启方式、原窗状态和物业要求，后续报价以实测数据为准。',
  },
  {
    pattern: /门店|地址|哪里|城市|广州|深圳|北京|佛山|东莞|体验中心/,
    intent: 'store',
    answer: '“城市门店”栏目只展示后台已发布的真实门店。你可以告诉我所在城市或小区，我会帮你整理预约信息；具体地址和电话请以门店页面为准。',
  },
  {
    pattern: /漏水|渗水|进水|返潮|排水孔|打胶|密封胶|雨水/,
    intent: 'waterproof',
    answer: '漏水要先判断是排水孔堵塞、外沿坡度、胶缝老化、窗框固定点还是墙体裂缝导致。不要只补一圈胶，建议现场检查排水路径、外侧收口和原窗台结构，再决定维修或换窗方案。',
  },
  {
    pattern: /阳台|封阳台|封窗|台风|抗风|渗水|漏水|排水|物业|审批/,
    intent: 'balcony',
    answer: '阳台封窗要重点看楼层风压、物业是否允许、外沿排水、窗框固定和打胶密封。报价通常由面积、型材系列、玻璃配置、开启扇数量、转角/立柱和施工难度决定，建议先测量现场再定方案。',
  },
  {
    pattern: /报价|价格|多少钱|费用|预算|贵不贵|单价|一平|每平|怎么算/,
    intent: 'quote',
    answer: '门窗报价不能只看单价，主要由洞口尺寸、楼层、型材壁厚、玻璃、五金、开启方式、拆旧收口和安装工艺决定。比较报价时建议看完整配置清单，避免只报低单价后期再加项。',
  },
  {
    pattern: /旧窗|改造|拆旧|换窗|老房|不动墙|窗框老化|漏风/,
    intent: 'renovation',
    answer: '旧窗改造会先确认原窗框是否拆除、墙体和窗台是否需要修补、是否影响外立面，以及室内保护方案。常见单户安装约 1–3 天，定制生产和排期以门店实测后确认为准。',
  },
  {
    pattern: /隔音|噪音|临街|高架|马路|睡眠|吵/,
    intent: 'soundproof',
    answer: '隔音窗要根据噪音类型选方案：低频车流声更看重玻璃厚度差、夹胶和密封；普通生活噪音可优先中空配置。除了玻璃，窗框密封、五金锁点和安装收口同样重要。',
  },
  {
    pattern: /断桥铝|型材|铝材|壁厚|系列|系统窗|系统门窗/,
    intent: 'profile',
    answer: '断桥铝要看型材系列、壁厚、隔热条、腔体结构和品牌来源。不是系列数字越大越好，关键是适不适合洞口尺寸、楼层风压、保温隔音需求和预算。',
  },
  {
    pattern: /玻璃|low-?e|中空|夹胶|三玻|钢化|保温|隔热|结露/,
    intent: 'glass',
    answer: '玻璃配置常见有中空钢化、夹胶中空、三玻两腔和 Low-E。临街优先关注隔音，西晒和保温场景可考虑 Low-E，安全需求高的阳台和落地窗建议确认钢化与夹胶配置。',
  },
  {
    pattern: /五金|执手|合页|锁点|纱窗|开启|内开|外开|推拉|平开/,
    intent: 'hardware',
    answer: '五金决定开启手感、密封压紧和长期稳定性。方案里应确认执手、合页、锁点、滑轮、纱窗和开启方式；高频使用的位置不要只看便宜配置。',
  },
  {
    pattern: /防盗门|入户门|门洞|锁芯|猫眼|门槛|门套|防盗等级/,
    intent: 'security_door',
    answer: '防盗门需要测量门洞尺寸、墙体厚度、开启方向、门槛高度和门套处理。锁芯等级、门体厚度、填充材料和安装固定方式都会影响安全性与价格。',
  },
  {
    pattern: /全屋|整屋|新房|装修|统一|定制/,
    intent: 'whole_house',
    answer: '全屋门窗建议统一测量、统一配置表和统一交付节点。不同房间可以按需求分级：卧室重隔音，客厅重采光和视野，厨房卫生间重通风和易清洁。',
  },
  {
    pattern: /质保|保修|售后|维修|坏了|松动|胶条|漏风|售后政策/,
    intent: 'warranty',
    answer: `售后以门店和产品质保政策为准。安装后建议保留合同、配置单和验收记录；五金松动、胶条老化、开启不顺或密封问题，可以拨打 ${SITE.hotlineDisplay} 或联系对应门店登记处理。`,
  },
  {
    pattern: /工期|多久|几天|生产|安装|施工|保护|灰尘|噪音/,
    intent: 'schedule',
    answer: '一般流程是预约沟通、上门测量、确认方案报价、下单生产、预约安装和验收。单户现场安装常见 1–3 天；生产周期要看产品类型、颜色、玻璃和门店排产。施工前会做地面和家具保护。',
  },
  {
    pattern: /付款|定金|尾款|合同|发票|验收/,
    intent: 'contract',
    answer: '下单前建议确认合同里的型材、玻璃、五金、颜色、面积计算方式、增项边界、工期、质保和验收标准。付款节点以门店合同为准，尽量不要只凭口头报价决定。',
  },
  {
    pattern: /保养|清洁|维护|怎么擦|轨道|排水孔/,
    intent: 'maintenance',
    answer: '日常维护可以定期清理轨道和排水孔，检查胶条是否脱落，五金铰链保持干净顺畅。不要用强腐蚀清洁剂擦型材表面，发现开启卡顿及时联系门店调试。',
  },
];

export function getCustomerServiceFaqAnswer(message: string): CustomerServiceFaqAnswer {
  const text = message.trim();
  const hit = FAQ_RULES.find((rule) => rule.pattern.test(text));
  if (hit) {
    return {
      answer: hit.answer,
      intent: hit.intent,
      handoff: Boolean(hit.handoff),
      source: 'faq',
    };
  }
  return {
    answer: '这个问题我先帮你记录。你可以补充城市、小区、楼层、需求、预算和大概尺寸；如果需要人工，我也可以直接切换到人工咨询。',
    intent: 'unknown',
    handoff: false,
    source: 'faq',
  };
}
