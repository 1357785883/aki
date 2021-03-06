import re

from nonebot import CommandSession, CommandGroup
from nonebot import on_natural_language, NLPSession, NLPResult
from nonebot.helpers import render_expression as __

from aki import nlp
from aki.command import allow_cancellation
from . import expressions as e

w = CommandGroup('weather')


@w.command('weather', aliases=('weather', '天气', '天气预报', '查天气'))
async def weather(session: CommandSession):
    location = session.get('location', prompt=__(e.WHERE))
    # time = session.get_optional('time')

    if location.province and not location.city and not location.district:
        # there is no city or district, ask the user for more info!
        session.get('location_more', prompt=__(e.WHERE_IN_PROVINCE,
                                               province=location.province))

    final_loc = location.heweather_format()
    await session.send(f'位置：{final_loc}')


@weather.args_parser
@allow_cancellation
async def _(session: CommandSession):
    striped_text_arg = session.current_arg_text.strip()
    if not striped_text_arg:
        # ignore empty argument
        return

    if not session.current_key:
        session.current_key = 'location'

    if session.current_key == 'location':
        location = await nlp.parse_location(striped_text_arg)
        if any((location.province, location.city, location.district)):
            session.args['location'] = location
    elif session.current_key == 'location_more':
        patched_loc = await nlp.parse_location(striped_text_arg)
        location: nlp.Location = session.args.get('location')
        assert location
        location.province = location.province or patched_loc.province
        location.city = location.city or patched_loc.city
        location.district = location.district or patched_loc.district
        session.args['location'] = location
    else:
        session.args[session.current_key] = striped_text_arg


@on_natural_language({'天气'})
async def _(session: NLPSession):
    text = re.sub(r'\s+', '', session.msg_text.strip())
    if not text:
        return

    confidence = 59.0

    if re.match(r'(?:怎么|咋)样\S{0,5}$', text) or \
            re.search(r'查(?:一?下|查看?)', text):
        confidence += 15.0
    if text.endswith('？') or text.endswith('?'):
        confidence += 5.0

    args = {}

    words = (await nlp.lexer(text))[0]
    for word in words:
        if word['ne'] == 'LOC':
            location = await nlp.parse_location(word['basic_words'])
            if any((location.province, location.city, location.district)):
                args['location'] = location
        elif word['ne'] == 'TIME':
            args['time'] = word['item']

    confidence += len(args) * 10.0 / 2.0 + 10.0 if args else 0.0
    return NLPResult(min(confidence, 100.0), ('weather', 'weather'), args)

# @on_natural_language({'雨', '雪', '晴', '阴', '冰雹', '雾'})
# async def _(session: NLPSession):
#     text = session.msg_text.strip()
#     from pprint import pprint
#     pprint(await nlp.lexer(text))
#
#     # if not ('?' in session.msg_text or '？' in session.msg_text):
#     #     return None
#     # return NLPResult(90.0, ('weather', 'weather'), {})
