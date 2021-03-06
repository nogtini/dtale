import json

import dash_core_components as dcc
import dash_daq as daq
import dash_html_components as html
import plotly
from pkg_resources import parse_version

from dtale.charts.utils import YAXIS_CHARTS, ZAXIS_CHARTS, find_group_vals
from dtale.utils import (ChartBuildingError, classify_type, dict_merge,
                         flatten_lists, get_dtypes, inner_build_query,
                         make_list)


def test_plotly_version(version_num):
    return parse_version(plotly.__version__) >= parse_version(version_num)


def base_layout(github_fork, **kwargs):
    """
    Base layout to be returned by :meth:`dtale.dash_application.views.DtaleDash.interpolate_index`

    :param github_fork: `True` if "Fork me on Github" banner should be displayed, `False` otherwise
    :type github_fork: bool
    :param kwargs: Optional keyword arguments to be passed to 'dash.Dash.interplolate_index'
    :type kwargs: dict
    :return: HTML
    :rtype: str
    """
    back_to_data_padding, github_fork_html = ('', '')
    if github_fork:
        back_to_data_padding = 'padding-right: 125px'
        github_fork_html = '''
            <span id="forkongithub">
                <a href="https://github.com/man-group/dtale">Fork me on GitHub</a>
            </span>
        '''
    return '''
        <!DOCTYPE html>
        <html>
            <head>
                {metas}
                <title>D-Tale Charts</title>
                <link rel="shortcut icon" href="../../images/favicon.png">
                {css}
            </head>
            <body>
                {github_fork_html}
                <div class="container-fluid charts">
                    <div class="row" style="margin: 0">
                        <div class="col-auto">
                            <header>
                                <span class="title-font">D-TALE</span>
                                <span style="font-size: 16px" class="pl-4">Charts</span>
                            </header>
                        </div>
                        <div class="col"></div>
                        <div class="col-auto mt-4" style="{back_to_data_padding}">
                            <a href="#" onclick="javascript:backToData()">
                                <i class="fas fa-th mr-4"></i>
                                <span>Back To Data</span>
                            </a>
                        </div>
                    </div>
                    {app_entry}
                </div>
                <footer>
                    {config}
                    {scripts}
                    <script type="text/javascript">
                        const pathSegs = window.location.pathname.split('/');
                        const dataId = pathSegs[pathSegs.length - 1];
                        const backToData = () => window.open('/dtale/main/' + dataId);
                        const goToLegacy = () => location.replace('/dtale/popup/charts/' + dataId);
                    </script>
                    {renderer}
                    {css}
                </footer>
            </body>
        </html>
    '''.format(
        metas=kwargs['metas'],
        css=kwargs['css'],
        app_entry=kwargs['app_entry'],
        config=kwargs['config'],
        scripts=kwargs['scripts'],
        renderer=kwargs['renderer'],
        back_to_data_padding=back_to_data_padding,
        github_fork_html=github_fork_html
    )


def build_input(label, input, className='col-auto', **kwargs):
    """
    Helper function to build a standard label/input component in dash.

    :param label: name of the input you are displaying
    :type label: str
    :param input: dash component for storing state
    :param className: style class to be applied to encapsulating div
    :type className: str
    :param kwargs: Optional keyword arguments to be applied to encapsulating div (style, title, id...)
    :type kwargs: dict
    :return: dash components for label/input
    :rtype: :dash:`dash_html_components.Div <dash-html-components/div>`
    """
    return html.Div(
        [
            html.Div(
                [html.Span(label, className='input-group-addon'), input],
                className='input-group mr-3',
            )
        ],
        className=className, **kwargs
    )


def build_tab(label, value, additional_style=None, **kwargs):
    """
    Builds a :dash:`dash_core_components.Tab <dash-core-components/tab>` with standard styling settings.
    """
    base_style = {'borderBottom': '1px solid #d6d6d6', 'padding': '6px'}
    return dcc.Tab(
        label=label,
        value=value,
        style=dict_merge(base_style, {'fontWeight': 'bold'}, additional_style or {}),
        disabled_style=dict_merge(
            base_style,
            {'fontWeight': 'bold', 'backgroundColor': 'LightGray', 'color': 'black', 'cursor': 'not-allowed'},
            additional_style or {}
        ),
        selected_style=dict_merge(
            base_style,
            {'borderTop': '1px solid #d6d6d6', 'backgroundColor': '#2a91d1', 'color': 'white'},
            additional_style or {}
        ), **kwargs)


def build_option(value, label=None):
    """
    Returns value/label inputs in a dictionary for use in
    :dash:`dash_core_components.Dropdown <dash-core-components/Dropdown>`
    """
    return {'label': label or value, 'value': value}


CHARTS = [
    dict(value='line'), dict(value='bar'), dict(value='scatter'), dict(value='pie'), dict(value='wordcloud'),
    dict(value='heatmap'), dict(value='3d_scatter', label='3D Scatter'), dict(value='surface'),
    dict(value='maps', label='Maps')
]
CHART_INPUT_SETTINGS = {
    'line': dict(x=dict(type='single'), y=dict(type='multi'), z=dict(display=False),
                 group=dict(display=True, type='single')),
    'bar': dict(x=dict(type='single'), y=dict(type='multi'), z=dict(display=False),
                group=dict(display=True, type='single')),
    'scatter': dict(x=dict(type='single'), y=dict(type='multi'), z=dict(display=False),
                    group=dict(display=True, type='single')),
    'pie': dict(x=dict(type='single'), y=dict(type='multi'), z=dict(display=False),
                group=dict(display=True, type='single')),
    'wordcloud': dict(x=dict(type='single'), y=dict(type='multi'), z=dict(display=False),
                      group=dict(display=True, type='single')),
    'heatmap': dict(x=dict(type='single'), y=dict(type='single'), z=dict(display=True, type='single'),
                    group=dict(display=False)),
    '3d_scatter': dict(x=dict(type='single'), y=dict(type='single'), z=dict(display=True, type='single'),
                       group=dict(display=True)),
    'surface': dict(x=dict(type='single'), y=dict(type='single'), z=dict(display=True, type='single'),
                    group=dict(display=False)),
}
AGGS = dict(
    count='Count', nunique='Unique Count', sum='Sum', mean='Mean', rolling='Rolling', corr='Correlation', first='First',
    last='Last', median='Median', min='Minimum', max='Maximum', std='Standard Deviation', var='Variance',
    mad='Mean Absolute Deviation', prod='Product of All Items', raw='No Aggregation'
)
FREQS = ['H', 'H2', 'WD', 'D', 'W', 'M', 'Q', 'Y']
FREQ_LABELS = dict(H='Hourly', H2='Hour', WD='Weekday', W='Weekly', M='Monthly', Q='Quarterly', Y='Yearly')

SCOPES = ['world', 'usa', 'europe', 'asia', 'africa', 'north america', 'south america']
PROJECTIONS = ['equirectangular', 'mercator', 'orthographic', 'natural earth', 'kavrayskiy7', 'miller', 'robinson',
               'eckert4', 'azimuthal equal area', 'azimuthal equidistant', 'conic equal area', 'conic conformal',
               'conic equidistant', 'gnomonic', 'stereographic', 'mollweide', 'hammer', 'transverse mercator',
               'albers usa', 'winkel tripel', 'aitoff', 'sinusoidal']

COLORSCALES = ['Blackbody', 'Bluered', 'Blues', 'Earth', 'Electric', 'Greens', 'Greys', 'Hot', 'Jet', 'Picnic',
               'Portland', 'Rainbow', 'RdBu', 'Reds', 'Viridis', 'YlGnBu', 'YlOrRd']

ANIMATION_CHARTS = ['line', 'bar', '3d_scatter']


def show_input_handler(chart_type):
    settings = CHART_INPUT_SETTINGS.get(chart_type or 'line') or {}

    def _show_input(input_id, input_type='single'):
        cfg = settings.get(input_id, {})
        return cfg.get('display', True) and cfg.get('type', 'single') == input_type
    return _show_input


def update_label_for_freq(val):
    """
    Formats sub-values contained within 'val' to display date frequencies if included.
        - (val=['a', 'b', 'c']) => 'a, b, c'
        - (val=['a|H', 'b', 'c']) => 'a (Hour), b, c'
    """

    def _freq_handler(sub_val):
        for freq in FREQS:
            if sub_val.endswith('|{}'.format(freq)):
                col, freq = sub_val.split('|')
                if freq in FREQ_LABELS:
                    return '{} ({})'.format(col, FREQ_LABELS[freq])
                return col
        return sub_val
    return ', '.join([_freq_handler(sub_val) for sub_val in make_list(val)])


def build_error(error, tb):
    """
    Returns error/traceback information in standard component with styling

    :param error: execption message
    :type error: str
    :param tb: traceback
    :type tb: str
    :return: error component
    :rtype: :dash:`dash_html_components.Div <dash-html-components/div>`
    """
    if isinstance(error, ChartBuildingError):
        if error.details:
            tb = error.details
        error = error.error
    return html.Div([
        html.I(className='ico-error'), html.Span(str(error)), html.Div(html.Pre(str(tb)), className='traceback')
    ], className='dtale-alert alert alert-danger')


def build_cols(cols, dtypes):
    """
    Helper function to add additional column entries for columns of type datetime so that users can make use of
    different frequencies of dates.  For example, hour, weekday, month, quarter, year

    :param cols: columns in dataframe
    :type cols: list of strings
    :param dtypes: datatypes of columns in dataframe
    :type dtypes: dict
    :return: generator or columns + any additional (datetime column + frequency) options
    """
    for c in cols:
        if classify_type(dtypes[c]) == 'D':
            for freq in FREQS:
                if freq in FREQ_LABELS:
                    yield '{}|{}'.format(c, freq), '{} ({})'.format(c, FREQ_LABELS[freq])
                else:
                    yield c, c
        else:
            yield c, c


def build_selections(*args):
    """
    simple helper function to build a single level list of values based on variable number of inputs which could be
    equal to None.
    """
    return flatten_lists([[] if a is None else make_list(a) for a in args])


def build_input_options(df, **inputs):
    """
    Builds dropdown options for (X, Y, Z, Group, Barsort & Y-Axis Ranges) with filtering based on currently selected
    values for the following inputs: x, y, z, group.
    """
    chart_type, x, y, z, group = (inputs.get(p) for p in ['chart_type', 'x', 'y', 'z', 'group'])
    col_opts = list(build_cols(df.columns, get_dtypes(df)))
    group_val, z_val = (None, z) if chart_type in ZAXIS_CHARTS else (group, None)
    x_options = [build_option(c, l) for c, l in col_opts if c not in build_selections(y, z_val, group_val)]
    y_filter = build_selections(x, group_val, z_val)
    y_multi_options = [build_option(c, l) for c, l in col_opts if c not in y_filter]
    y_single_options = [build_option(c, l) for c, l in col_opts if c not in y_filter]
    z_options = [build_option(c) for c in df.columns if c not in build_selections(x, y, group_val)]
    group_options = [build_option(c, l) for c, l in col_opts if c not in build_selections(x, y, z_val)]
    barsort_options = [build_option(o) for o in build_selections(x, y)]
    yaxis_options = [build_option(y2) for y2 in y or []]

    return x_options, y_multi_options, y_single_options, z_options, group_options, barsort_options, yaxis_options


def build_map_options(df, type='choropleth', loc=None, lat=None, lon=None, map_val=None):
    lat_options = [build_option(c) for c in df.columns if c not in build_selections(lon, map_val)]
    lon_options = [build_option(c) for c in df.columns if c not in build_selections(lat, map_val)]
    loc_options = [build_option(c) for c in df.columns if c not in build_selections(map_val)]
    if type == 'choropleth':
        val_options = [build_option(c) for c in df.columns if c not in build_selections(loc)]
    else:
        val_options = [build_option(c) for c in df.columns if c not in build_selections(lon, lat)]
    return loc_options, lat_options, lon_options, val_options


def bar_input_style(**inputs):
    """
    Sets display CSS property for bar chart inputs
    """
    return dict(display='block' if inputs.get('chart_type') == 'bar' else 'none')


def colorscale_input_style(**inputs):
    return dict(display='block' if inputs.get('chart_type') in ['heatmap', 'maps'] else 'none')


def animate_input_style(**inputs):
    chart_type, cpg = (inputs.get(p) for p in ['chart_type', 'cpg'])
    show = not cpg and chart_type in ANIMATION_CHARTS and test_plotly_version('4.4.1')
    return dict(display='block' if show else 'none')


def show_chart_per_group(**inputs):
    """
    Boolean function to determine whether "Chart Per Group" toggle should be displayed or not
    """
    [chart_type, group] = [inputs.get(p) for p in ['chart_type', 'group']]
    invalid_type = chart_type in ['pie', 'wordcloud', 'maps']
    return show_input_handler(chart_type)('group') and len(group or []) and not invalid_type


def show_yaxis_ranges(**inputs):
    """
    Boolean function to determine whether "Y-Axis Range" inputs should be displayed or not
    """
    chart_type, y = (inputs.get(p) for p in ['chart_type', 'y'])
    return chart_type in YAXIS_CHARTS and len(y or [])


def get_yaxis_type_tabs(y):
    tabs = [
        build_tab('Default', 'default', {'padding': '2px', 'minWidth': '4em'}),
        build_tab('Single', 'single', {'padding': '2px', 'minWidth': '4em'}),
    ]
    if len(y) <= 1:
        return tabs
    return tabs + [build_tab('Multi', 'multi', {'padding': '2px', 'minWidth': '4em'})]


def build_group_val_options(df, group_cols):
    group_vals = find_group_vals(df, group_cols)
    return [
        build_option(json.dumps(gv), '|'.join([str(gv.get(p, 'NaN')) for p in group_cols]))
        for gv in group_vals
    ]


def main_inputs_and_group_val_display(inputs):
    group_cols = make_list(inputs.get('group'))
    if not show_input_handler(inputs.get('chart_type', 'line'))('group') or not len(group_cols):
        return dict(display='none'), 'col-md-12'
    return dict(display='block'), 'col-md-8'


def charts_layout(df, settings, **inputs):
    """
    Builds main dash inputs with dropdown options populated with the columns of the dataframe associated with the
    page. Inputs included are: chart tabs, query, x, y, z, group, aggregation, rolling window/computation,
    chart per group toggle, bar sort, bar mode, y-axis range editors

    :param df: dataframe to drive the charts built on page
    :type df: :class:`pandas:pandas.DataFrame`
    :param settings: global settings associated with this dataframe (contains properties like "query")
    :type param: dict
    :return: dash markup
    """
    chart_type, x, y, z, group, agg = (inputs.get(p) for p in ['chart_type', 'x', 'y', 'z', 'group', 'agg'])
    y = y or []
    show_input = show_input_handler(chart_type)
    show_cpg = show_chart_per_group(**inputs)
    show_yaxis = show_yaxis_ranges(**inputs)
    bar_style = bar_input_style(**inputs)
    animate_style = animate_input_style(**inputs)

    options = build_input_options(df, **inputs)
    x_options, y_multi_options, y_single_options, z_options, group_options, barsort_options, yaxis_options = options
    query_placeholder = (
        "Enter pandas query (ex: col1 == 1)"
    )
    query_value = inputs.get('query') or inner_build_query(settings, settings.get('query'))
    query_label = html.Div([
        html.Span('Query'),
        html.A(html.I(className='fa fa-info-circle ml-4'),
               href='https://pandas.pydata.org/pandas-docs/stable/user_guide/indexing.html#indexing-query',
               target='_blank', style={'color': 'white'})
    ], className='input-group-addon', style={'minWidth': '7em'})
    yaxis_type = (inputs.get('yaxis') or {}).get('type') or 'default'
    yaxis_type_style = {'borderRadius': '0 0.25rem 0.25rem 0'} if yaxis_type == 'default' else None
    show_map = chart_type == 'maps'
    map_props = ['map_type', 'loc_mode', 'loc', 'lat', 'lon', 'map_val']
    map_type, loc_mode, loc, lat, lon, map_val = (inputs.get(p) for p in map_props)
    loc_options, lat_options, lon_options, map_val_options = build_map_options(df, type=map_type, loc=loc, lat=lat,
                                                                               lon=lon, map_val=map_val)
    cscale_style = colorscale_input_style(**inputs)
    default_cscale = 'Greens' if chart_type == 'heatmap' else 'Reds'

    group_val_style, main_input_class = main_inputs_and_group_val_display(inputs)
    group_val = [json.dumps(gv) for gv in inputs.get('group_val') or []]

    def show_style(show):
        return {'display': 'block' if show else 'none'}

    def show_map_style(show):
        return {} if show else {'display': 'none'}
    return html.Div([
        dcc.Store(id='query-data', data=inputs.get('query')),
        dcc.Store(id='input-data', data={k: v for k, v in inputs.items() if k not in ['cpg', 'barmode', 'barsort']}),
        dcc.Store(id='chart-input-data', data={k: v for k, v in inputs.items() if k in ['cpg', 'barmode', 'barsort']}),
        dcc.Store(
            id='map-input-data',
            data={k: v for k, v in inputs.items() if k in ['map_type', 'map_code', 'lat', 'lon', 'map_val', 'scope',
                                                           'proj']}
        ),
        dcc.Store(id='range-data'),
        dcc.Store(id='yaxis-data', data=inputs.get('yaxis')),
        dcc.Store(id='last-chart-input-data', data=inputs),
        dcc.Input(id='chart-code', type='hidden'),
        html.Div(html.Div(dcc.Tabs(
            id='chart-tabs',
            value=chart_type or 'line',
            children=[build_tab(t.get('label', t['value'].capitalize()), t['value']) for t in CHARTS],
            style=dict(height='36px')
        ), className='col-md-12'), className='row pt-3 pb-3 charts-filters'),
        html.Div(html.Div([
            html.Div([
                query_label, dcc.Input(
                    id='query-input', type='text', placeholder=query_placeholder, className='form-control',
                    value=query_value, style={'lineHeight': 'inherit'})
            ], className='input-group mr-3')],
            className='col'
        ), className='row pt-3 pb-3 charts-filters'),
        html.Div(
            [html.Div([
                html.Div(
                    [
                        build_input('X', dcc.Dropdown(
                            id='x-dropdown',
                            options=x_options,
                            placeholder='Select a column',
                            value=x,
                            style=dict(width='inherit'),
                        )),
                        build_input(
                            'Y',
                            dcc.Dropdown(
                                id='y-multi-dropdown',
                                options=y_multi_options,
                                multi=True,
                                placeholder='Select a column(s)',
                                style=dict(width='inherit'),
                                value=y if show_input('y', 'multi') else None
                            ),
                            className='col',
                            id='y-multi-input',
                            style=show_style(show_input('y', 'multi'))
                        ),
                        build_input('Y', dcc.Dropdown(
                            id='y-single-dropdown',
                            options=y_single_options,
                            placeholder='Select a column',
                            style=dict(width='inherit'),
                            value=y[0] if show_input('y') and len(y) else None
                        ), className='col', id='y-single-input', style=show_style(show_input('y'))),
                        build_input('Z', dcc.Dropdown(
                            id='z-dropdown',
                            options=z_options,
                            placeholder='Select a column',
                            style=dict(width='inherit'),
                            value=z
                        ), className='col', id='z-input', style=show_style(show_input('z'))),
                        build_input(
                            'Group',
                            dcc.Dropdown(
                                id='group-dropdown',
                                options=group_options,
                                multi=True,
                                placeholder='Select a group(s)',
                                value=group,
                                style=dict(width='inherit'),
                            ),
                            className='col',
                            id='group-input',
                            style=show_style(show_input('group'))
                        )
                    ],
                    id='non-map-inputs', style={} if not show_map else {'display': 'none'},
                    className='row pt-3 pb-3 charts-filters'
                ),
                html.Div(
                    [
                        build_input('Map Type', dcc.Dropdown(
                            id='map-type-dropdown',
                            options=[build_option(v, v.capitalize()) for v in ['choropleth', 'scattergeo']],
                            value=map_type or 'choropleth',
                            style=dict(width='inherit'),
                            className='map-dd'
                        )),
                        build_input('Location Mode', dcc.Dropdown(
                            id='map-loc-mode-dropdown',
                            options=[build_option(v) for v in ["ISO-3", "USA-states", "country names"]],
                            style=dict(width='inherit'),
                            value=loc_mode
                        ), id='map-loc-mode-input', style=show_map_style(map_type == 'choropleth')),
                        build_input('Locations', dcc.Dropdown(
                            id='map-loc-dropdown',
                            options=loc_options,
                            placeholder='Select a column',
                            value=loc,
                            style=dict(width='inherit'),
                        ), id='map-loc-input', style=show_map_style(map_type == 'choropleth')),
                        build_input('Lat', dcc.Dropdown(
                            id='map-lat-dropdown',
                            options=lat_options,
                            placeholder='Select a column',
                            value=lat,
                            style=dict(width='inherit'),
                        ), id='map-lat-input', style=show_map_style(map_type == 'scattergeo')),
                        build_input('Lon', dcc.Dropdown(
                            id='map-lon-dropdown',
                            options=lon_options,
                            placeholder='Select a column',
                            style=dict(width='inherit'),
                            value=lon
                        ), id='map-lon-input', style=show_map_style(map_type == 'scattergeo')),
                        build_input('Value', dcc.Dropdown(
                            id='map-val-dropdown',
                            options=map_val_options,
                            placeholder='Select a column',
                            style=dict(width='inherit'),
                            value=map_val
                        )),
                        build_input('Scope', dcc.Dropdown(
                            id='map-scope-dropdown',
                            options=[build_option(v) for v in SCOPES],
                            style=dict(width='inherit'),
                            value='world'
                        ), id='map-scope-input', style=show_map_style(map_type == 'scattergeo')),
                        build_input('Projection', dcc.Dropdown(
                            id='map-proj-dropdown',
                            options=[build_option(v) for v in PROJECTIONS],
                            style=dict(width='inherit'),
                            value=None
                        ), id='map-proj-input', style=show_map_style(map_type == 'scattergeo')),
                    ],
                    id='map-inputs', className='row pt-3 pb-3 charts-filters',
                    style={} if show_map else {'display': 'none'}
                ),
                html.Div([
                    build_input('Aggregation', dcc.Dropdown(
                        id='agg-dropdown',
                        options=[build_option(v, AGGS[v]) for v in ['count', 'nunique', 'sum', 'mean', 'rolling',
                                                                    'corr', 'first', 'last', 'median', 'min', 'max',
                                                                    'std', 'var', 'mad', 'prod', 'raw']],
                        placeholder='Select an aggregation',
                        style=dict(width='inherit'),
                        value=agg or 'raw',
                    )),
                    html.Div([
                        build_input('Window', dcc.Input(
                            id='window-input', type='number', placeholder='Enter days',
                            className='form-control text-center', style={'lineHeight': 'inherit'},
                            value=inputs.get('window')
                        )),
                        build_input('Computation', dcc.Dropdown(
                            id='rolling-comp-dropdown',
                            options=[
                                build_option('corr', 'Correlation'),
                                build_option('count', 'Count'),
                                build_option('cov', 'Covariance'),
                                build_option('kurt', 'Kurtosis'),
                                build_option('max', 'Maximum'),
                                build_option('mean', 'Mean'),
                                build_option('median', 'Median'),
                                build_option('min', 'Minimum'),
                                build_option('skew', 'Skew'),
                                build_option('std', 'Standard Deviation'),
                                build_option('sum', 'Sum'),
                                build_option('var', 'Variance'),
                            ],
                            placeholder='Select an computation',
                            style=dict(width='inherit'), value=inputs.get('rolling_comp')
                        ))
                    ], id='rolling-inputs', style=show_style(agg == 'rolling'))
                ], className='row pt-3 pb-3 charts-filters'),
                html.Div(
                    [
                        build_input('Chart Per\nGroup',
                                    html.Div(daq.BooleanSwitch(id='cpg-toggle', on=inputs.get('cpg') or False),
                                             className='toggle-wrapper'),
                                    id='cpg-input', style=show_style(show_cpg), className='col-auto'),
                        build_input('Barmode', dcc.Dropdown(
                            id='barmode-dropdown',
                            options=[
                                build_option('group', 'Group'),
                                build_option('stack', 'Stack'),
                                build_option('relative', 'Relative'),
                            ],
                            value=inputs.get('barmode') or 'group',
                            placeholder='Select a mode',
                        ), className='col-auto addon-min-width', style=bar_style, id='barmode-input'),
                        build_input('Barsort', dcc.Dropdown(
                            id='barsort-dropdown', options=barsort_options, value=inputs.get('barsort')
                        ), className='col-auto addon-min-width', style=bar_style, id='barsort-input'),
                        html.Div(
                            html.Div(
                                [
                                    html.Span('Y-Axis', className='input-group-addon'),
                                    html.Div(
                                        dcc.Tabs(
                                            id='yaxis-type',
                                            value=yaxis_type,
                                            children=get_yaxis_type_tabs(y),
                                        ),
                                        id='yaxis-type-div',
                                        className='form-control col-auto pt-3',
                                        style=yaxis_type_style
                                    ),
                                    dcc.Dropdown(id='yaxis-dropdown', options=yaxis_options),
                                    html.Span('Min:', className='input-group-addon col-auto', id='yaxis-min-label'),
                                    dcc.Input(
                                        id='yaxis-min-input', type='number', className='form-control col-auto',
                                        style={'lineHeight': 'inherit'}
                                    ),
                                    html.Span('Max:', className='input-group-addon col-auto', id='yaxis-max-label'),
                                    dcc.Input(
                                        id='yaxis-max-input', type='number', className='form-control col-auto',
                                        style={'lineHeight': 'inherit'}
                                    )
                                ],
                                className='input-group', id='yaxis-min-max-options',
                            ),
                            className='col-auto addon-min-width', id='yaxis-input',
                            style=show_style(show_yaxis)
                        ),
                        build_input('Colorscale', dcc.Dropdown(
                            id='colorscale-dropdown', options=[build_option(o) for o in COLORSCALES],
                            value=inputs.get('colorscale') or default_cscale
                        ), className='col-auto addon-min-width', style=cscale_style, id='colorscale-input'),
                        build_input(
                            'Animate',
                            html.Div(daq.BooleanSwitch(id='animate-toggle', on=inputs.get('animate') or False),
                                     className='toggle-wrapper'),
                            id='animate-input',
                            style=animate_style,
                            className='col-auto'
                        ),
                    ],
                    className='row pt-3 pb-5 charts-filters'
                )],
                id='main-inputs', className=main_input_class
            ), build_input('Group(s)', dcc.Dropdown(
                id='group-val-dropdown',
                multi=True,
                placeholder='Select a group value(s)',
                value=group_val,
                style=dict(width='inherit'),
            ), className='col-md-4 pt-3 pb-5', id='group-val-input', style=group_val_style)],
            className='row'
        ),
        dcc.Loading(html.Div(id='chart-content', style={'height': '69vh'}), type='circle'),
        dcc.Textarea(id="copy-text", style=dict(position='absolute', left='-110%'))
    ], className='charts-body')
