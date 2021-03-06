#!/usr/bin/env python

import copy
import readline
import sys
import re

class SimpleCompleter(object):

  def __init__(self, options):
    self.options = sorted(options)
    return

  def complete(self, text, state):
    response = None
    if state == 0:
      # This is the first time for this text, so build a match list.
      if text:
        self.matches = [s for s in self.options if s and s.startswith(text)]
      else:
        self.matches = self.options[:]

    # Return the state'th item from the match list, if we have that many.
    try:
      response = self.matches[state]
    except IndexError:
      response = None
    return response

class PandemicInfections(object):

  def __init__(self, cities_file, state_filename='state.txt'):
    self.cities = []
    self.stack = []
    self.cards_drawn = []
    self.state_filename = state_filename
    self.level = 2
    self.setup(cities_file)

  def setup(self, cities_file):
    self.read_cities(cities_file)
    self.stack = [copy.copy(self.cities)]
    # Register the completer function and bind tab
    options = copy.copy(self.cities)
    options = sorted(set(options), key=options.index)
    options.append('READ')
    options.append('EPIDEMIC')
    readline.set_completer(SimpleCompleter(options).complete)
    readline.parse_and_bind('tab: complete')

  def set_level(self):
    question = 'Set infection level to? '
    impossible = 'Invalid input! Please enter a number.'
    line = input(question)
    while not re.match('^\d+$', line):
      print(impossible)
      line = input(question)
    self.level = int(line)

  def read_cities(self, filename):
    # Read input file with city names.
    self.cities = []
    with open(filename, 'r') as f:
      for line in f:
        line = line.strip('\n')
        if not line or line.startswith('#'):
          continue
        if '*' in line:
          n, city = line.split('*')
          self.cities += int(n) * [city]
        else:
          self.cities += [line]

  def draw_card(self, line):
    # Draw card from the top of the stack and add it to the discard pile.
    self.cards_drawn.append(line)
    assert(self.stack[-1])
    self.stack[-1].remove(line)
    if not self.stack[-1]:
      self.stack.pop()

  def epidemic(self):
    question = 'Which city was drawn from the bottom in the Epidemic? '
    impossible = 'This is impossible!'
    # Draw card from front of the stack ("the bottom")
    line = input(question)
    assert(self.stack)
    front_pile = self.stack[0]
    while not line in front_pile:
      print(impossible)
      line = input(question)
    self.cards_drawn.append(line)
    # Remove card from front pile and remove it from the stack if it is now empty.
    front_pile.remove(line)
    if not front_pile:
      del self.stack[0]
    # Push discard pile on stack and reset it.
    self.stack.append(sorted(self.cards_drawn))
    self.cards_drawn = []

  def print_state(self, f=sys.stdout):
    # Print the draw deck with sections
    i = 0
    print('', file=f)
    print('############################', file=f)
    print('###       The Deck       ###', file=f)
    for x in self.stack:
      for city in sorted(set(x), key=lambda v: x.count(v), reverse=True):
        print('%d * %s' % (x.count(city), city), file=f)
      i += 1
      if i != len(self.stack):
        print('----------------------------', file=f)
    print('############################', file=f)
    # Print the discard pile
    print('', file=f)
    print('############################', file=f)
    print('###       Discard        ###', file=f)
    for city in sorted(set(self.cards_drawn), key=lambda v: self.cards_drawn.count(v), reverse=True):
      print('%d * %s' % (self.cards_drawn.count(city), city), file=f)
    print('############################', file=f)

  def write_state(self):
    # Write the current state to disk
    with open(self.state_filename, 'a') as f:
      self.print_state(f=f)

  def read_state(self):
    # Read the current state from disk
    self.stack = []
    self.cards_drawn = []
    phase = ''
    with open(self.state_filename, 'r') as f:
      for line in f:
        line = line.strip('\n')
        if 'The Deck' in line:
          self.stack = [[]]
          self.cards_drawn = []
          phase = 'deck'
        elif 'Discard' in line:
          phase = 'discard'
        if phase == 'deck' and line.startswith('-----'):
          self.stack.append([])
        if not re.search('^\d+ \* \w+$', line):
          continue
        occurences, _, city = line.split(' ')
        for k in range(int(occurences)):
          if phase == 'deck':
            self.stack[-1].append(city)
          elif phase == 'discard':
            self.cards_drawn.append(city)
          else:
            assert(False)

  def calculate_probability(self, city, M, N, stack=None):
    if stack is None:
      stack = copy.deepcopy(self.stack)
      N_cards = sum([len(x) for x in stack])
      N = min(N, N_cards)

    # Stop conditions
    if M == 0:
      return 1.0
    if M > N:
      return 0.0

    assert(M >= 1)
    assert(N >= 1)
    assert(stack)

    pile = stack.pop()
    count = pile.count(city)
    total = len(pile)
    assert(total > 0)
    p_city = count / total

    # If there was only one card to draw: This is the leaf probability
    if N == 1:
      return p_city

    # Prepare two new piles, one with the city removed and one with some other city removed (if any)
    pile1 = copy.copy(pile)
    if city in pile1:
      pile1.remove(city)
    pile2 = copy.copy(pile)
    for x in pile2:
      if x != city:
        pile2.remove(x)
        break

    # Add the two new piles to two stacks
    stack1 = copy.copy(stack)
    stack2 = copy.copy(stack)
    if pile1:
      stack1.append(pile1)
    if pile2:
      stack2.append(pile2)

    # Add the two branch probabilities
    p1 = (p_city       * self.calculate_probability(city, M-1, N-1, stack=stack1)) if p_city > 0.0 else 0.0
    p2 = ((1 - p_city) * self.calculate_probability(city, M,   N-1, stack=stack2)) if p_city < 1.0 else 0.0
    return p1 + p2

  def print_probabilities(self, f=sys.stdout):
    print('', file=f)

    header = '%-15s' % 'Name'
    for i in range(1, self.level + 1):
      header += ' %6s' % ("N>=%d" % i)
    print(header, file=f)
    print(len(header)*'-', file=f)

    probabilities = dict()
    for x in set(self.cities):
      probabilities[x] = []
      for M in range(1, self.level + 1):
        probabilities[x].append(self.calculate_probability(x, M, self.level))

    for x, p in sorted(probabilities.items(), key=lambda x: x[1][0], reverse=True):
      line = '%-15s ' % x
      for px in p:
        line += "%5.1f%% " % (100.0 * px)
      print(line, file=f)

  def write_probabilities(self):
    # Write the current state to disk
    with open(self.state_filename, 'a') as f:
      self.print_probabilities(f=f)

  def run(self):
    # The main input loop
    question = 'Please enter the name of the city which was drawn or "EPIDEMIC/READ": '
    impossible = 'This is impossible!'
    while True:
      # Get new input
      print()
      line = input(question)
      while line not in ['EPIDEMIC', 'READ', 'LEVEL'] and not line in self.stack[-1]:
        print(impossible)
        line = input(question)
      # Process
      if line == 'LEVEL':
        self.set_level()
      elif line == 'READ':
        self.read_state()
      elif line == 'EPIDEMIC':
        self.epidemic()
      else:
        self.draw_card(line)
      # Print current state and probabilities, write state to disk
      self.print_state()
      self.print_probabilities()
      self.write_state()
      self.write_probabilities()

# Start the input loop
cities_file = sys.argv[1]
output_file = sys.argv[2] if len(sys.argv) > 2 else 'state.txt'
p = PandemicInfections(cities_file=cities_file, state_filename=output_file)
p.run()
