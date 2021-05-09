import numpy
import pandas
from frictionless.schema import Schema
from frictionless.field import Field
from typing import List

from .base import BaseProcessor

class AppearancesProcessor(BaseProcessor):

  name = 'appearances'
  description = "Appearances for `players`. One row per appearance."

  def process(self):

    def cast_metric(metric):
      if len(metric) == 0:
        return 0
      else:
        return int(metric)

    def cast_minutes_played(minutes_played):
      if len(minutes_played) > 0:
        numeric = minutes_played[:-1]
        return int(numeric)
      else:
        return 0

    def create_surrogate_key(columns: List[str], df: pandas.DataFrame) -> pandas.DataFrame:
      games_df = df.drop_duplicates(subset=columns).sort_values(
        by=columns
      )[columns]
      return games_df.index.values + 1

    prep_df = pandas.DataFrame()

    json_normalized = pandas.json_normalize(self.raw_df.to_dict(orient='records'))

    self.set_checkpoint('json_normalized', json_normalized)

    domestic_competitions = [
      'ES1', 'GB1', 'L1', 'IT1', 'FR1', 'GR1', 'PO1', 'BE1', 'UKR1', 'BE1', 'RU1', 'DK1', 'SC1', 'TR1', 'NL1'
    ]
    json_normalized = json_normalized[json_normalized['competition_code'].isin(domestic_competitions)]

    self.set_checkpoint('json_normalized_filtered', json_normalized)
    
    prep_df['player_id'] = json_normalized['parent.href'].str.split('/', 5, True)[4] # .astype('int32')
    prep_df['game_id'] = json_normalized['result.href'].str.split('/', 5, True)[4]
    prep_df['appearance_id'] = create_surrogate_key(['player_id', 'game_id'], prep_df)
    prep_df['league_id'] = json_normalized['competition_code']
    prep_df['player_club_id'] = json_normalized['for.href'].str.split('/', 5, True)[4] # .astype('int32')
    prep_df['goals'] = json_normalized['goals'].apply(cast_metric)
    prep_df['assists'] = json_normalized['assists'].apply(cast_metric)
    prep_df['minutes_played'] = json_normalized['minutes_played'].apply(cast_minutes_played)
    prep_df['yellow_cards'] = (
      (json_normalized['yellow_cards'].str.len() > 0).astype('int32') + 
      (json_normalized['second_yellow_cards'].str.len() > 0).astype('int32')
    )
    prep_df['red_cards'] = (json_normalized['red_cards'].str.len() > 0).astype('int32')
    prep_df['url'] = 'https://www.transfermarkt.co.uk' + json_normalized['href']

    prep_df = prep_df.drop_duplicates()

    self.set_checkpoint('prep', prep_df)
    self.prep_df = prep_df

  def get_validations(self):
    return [
      # TODO: Implement checks as frictionless custom checks https://framework.frictionlessdata.io/docs/guides/validation-guide#custom-checks
      # 'assert_df_not_empty',
      # 'assert_minutes_played_gt_120',
      # 'assert_goals_in_range',
      # 'assert_assists_in_range',
      # 'assert_own_goals_in_range',
      # 'assert_yellow_cards_range',
      # 'assert_red_cards_range',
      # 'assert_unique_on_player_and_date',
      # 'assert_clubs_per_competition',
      # 'assert_appearances_per_match',
      # 'assert_appearances_per_club_per_game',
      # 'assert_appearances_freshness_is_less_than_one_week',
      # 'assert_goals_ne_assists',
      # 'assert_goals_ne_own_goals',
      # 'assert_yellow_cards_not_constant',
      # 'assert_red_cards_not_constant'
    ]

  def resource_schema(self):
    self.schema = Schema()

    self.schema.add_field(Field(name='player_id', type='integer'))
    self.schema.add_field(Field(name='game_id', type='integer'))
    self.schema.add_field(Field(name='appearance_id', type='integer'))
    self.schema.add_field(Field(name='league_id', type='string'))
    self.schema.add_field(Field(name='player_club_id', type='integer'))
    self.schema.add_field(Field(name='goals', type='integer'))
    self.schema.add_field(Field(name='assists', type='integer'))
    self.schema.add_field(Field(name='minutes_played', type='integer'))
    self.schema.add_field(Field(name='yellow_cards', type='integer'))
    self.schema.add_field(Field(name='red_cards', type='integer'))
    self.schema.add_field(Field(
      name='url',
      type='string',
      format='uri'
      )
    )
    
    self.schema.primary_key = ['appearance_id']
    
    self.schema.foreign_keys = [
      {"fields": "game_id", "reference": {"resource": "games", "fields": "game_id"}}
    ]

    return self.schema
