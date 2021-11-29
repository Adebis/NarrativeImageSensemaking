import sqlite3
from sqlite3 import Error

class DatabaseManager:

    # The file path to the concepts database
    concepts_db_file_path = ""

    # Whether we print verbose logs
    verbose = False

    def __init__(self, db_path=None):
        # Change this to True for debugging
        self.verbose = False
        if db_path == None:
            self.concepts_db_file_path = 'data/concept_data.db'
        else:
            self.concepts_db_file_path = db_path
    # end __init__

    # ===== GENERAL =====

    # Execute a sql command in the database.
    # Input: sql_command, the string for the sql command itself.
    #       command_data, a list of data values for the sql command.
    # Output: The return value of the operation.
    #       If the operation failed, return False. 
    def execute_command(self, sql_command, command_data=None):
        return_value = None
        # Open a connection to the database
        connection = sqlite3.connect(self.concepts_db_file_path)
        try:
            # Get a cursor to the database
            cursor = connection.cursor()
            # Execute the given sql command.
            if command_data == None:
                cursor.execute(sql_command)
            else:
                cursor.execute(sql_command, command_data)
            return_value = cursor.fetchall()
            # end if
            # Commit the changes to the database
            connection.commit()
        except Error as e:
            return_value = False
            if self.verbose:
                print("Error executing sql command " + sql_command + ": " + str(e))
                print(" data: " + str(command_data))
        # end try
        # Whether the command was executed successfully or not,
        # close the connection.
        self.close_connection(connection)
        # has been executed. 
        return return_value
    # end execute_command

    # Open a connection to the given database file. 
    # Returns the connection object. 
    # Returns None if a connection could not be made. 
    def open_connection(self, database_file_path):
        connection = None
        try:
            connection = sqlite3.connect(database_file_path)
        except Error as e:
            print("Error establishing connection to database "
                  + database_file_path
                  + ": " + str(e))
        return connection
    # end open_connection

    # Close the given connection.
    def close_connection(self, connection):
        try:
            connection.close()
        except Error as e:
            print("Error closing connection to database: " + str(e))
        return None
    # end close_connection

    # ===== END GENERAL =====

    # ===== INSERT =====

    # Insert a row into a table.
    #   Inputs: table_name, name of the table to insert into,
    #           row_data, list of data for the row
    #   Outputs: True if the insert operation was successful. 
    def insert_row(self, table_name, row_data):
        # Get the sql command to insert a row into the given table.
        sql_insert_command = self.get_insert_command(table_name)
        # Execute the sql command.
        insert_success = self.execute_command(sql_insert_command, row_data)
        return insert_success
    # end insert_row

    # Depending on the table name, build a different
    # sql insert command.
    def get_insert_command(self, table_name):
        sql_insert_command = ""
        if table_name == 'concepts':
            sql_insert_command = """ INSERT INTO concepts (name, queried)
                                 VALUES(?,?) """
        elif table_name == 'predicates':
            sql_insert_command = """ INSERT INTO predicates (name, source, relationship, target, weight)
                                 VALUES(?,?,?,?,?) """
        elif table_name == 'embeddings':
            sql_insert_command = " INSERT INTO embeddings VALUES(?"
            for i in range(300):
                sql_insert_command += ",?"
            # end for
            sql_insert_command += ");"
        # end if
        return sql_insert_command
    # end get_insert_command

    # ===== END INSERT =====

    # ===== DELETE =====

    # Delete a row whose column matches a certain value from a table.
    # Inputs: table_name, name of the table to delete from.
    #           column_name, name of the column to match the value of.
    #           matching_value, value of the column to match when looking
    #               for the row to delete. 
    # Outputs: True if the delete operation was successful.
    #           False otherwise.
    def delete_row(self, table_name, column_name, matching_value):
        # Check if the matching value is a string. If so,
        # place escape character quotes around it.
        if isinstance(matching_value, str):
            matching_value = "'" + matching_value + "'"
        # Construct the sql command to delete a row from
        # the given table using the given search conditions.
        search_condition = str(column_name) + " = " + str(matching_value)
        sql_delete_command = " DELETE FROM "
        sql_delete_command += str(table_name)
        sql_delete_command += " WHERE "
        sql_delete_command += str(search_condition)
        sql_delete_command += ";"
        # Execute the sql command.
        delete_success = self.execute_command(sql_delete_command)
        return delete_success
    # end delete_row
    
    # Delete all rows from a table.
    def delete_all_rows(self, table_name):
        # Build the sql command.
        sql_delete_command = " DELETE FROM "
        sql_delete_command += str(table_name) + ";"
        # Execute the sql command.
        delete_success = self.execute_command(sql_delete_command)
        return delete_success
    # end delete_all_rows

    # ===== END DELETE =====

    # ===== SELECT =====

    # Retrieve a row of data from the database using a select command.
    # Inputs: table_name, name of the table to select from.
    #           column_names, list of names of the columns to match.
    #           matching_values, list of values of the columns to match when looking
    #               for the rows to retrieve.
    # Outputs: the return values of the select command.
    #           If the rows are not found, returns an empty list []
    def select_row(self, table_name, column_names, matching_values):
        # Check if any matching value is a string. If so,
        # place escape character quotes around it.
        matching_values_parsed = list()
        for matching_value in matching_values:
            if isinstance(matching_value, str):
                matching_values_parsed.append("'" + matching_value + "'")
            else:
                matching_values_parsed.append(matching_value)
            # end else
        # end for

        # Get the sql command.
        sql_select_command = self.get_select_command(table_name, column_names, matching_values_parsed)
        # Execute the sql command.
        select_return = self.execute_command(sql_select_command)
        return select_return
    # end select_command

    # Make a select command matching a single column. 
    # Depending on the table name, build a different
    # sql select command.
    def get_select_command(self, table_name, column_names, matching_values):
        sql_insert_command = ""
        if table_name == 'concepts':
            sql_insert_command = "SELECT name, queried "
        elif table_name == 'predicates':
            sql_insert_command = "SELECT name, source, relationship, target, weight "
        elif table_name == 'embeddings':
            sql_insert_command = "SELECT name"
            # Get each of the 300 rows of floats
            for i in range(300):
                sql_insert_command += ', e' + str(i)
            # end for
        # end elif
        # Build the search conditions using the list of columns and matching values.
        search_conditions = ""
        for i in range(len(column_names)):
            if i > 0:
                search_conditions += " AND "
            # end if
            search_conditions += column_names[i] + " = " + str(matching_values[i])
        # end for
        sql_insert_command += " FROM " + str(table_name)
        # Only add a WHERE statement if there were search conditions
        if not search_conditions == "":
            sql_insert_command += " WHERE "
            sql_insert_command += search_conditions
        sql_insert_command += ";"
        
        if self.verbose:
            print(sql_insert_command)
            
        return sql_insert_command
    # end get_select_command

    # ===== END SELECT =====

    # ===== UTILITY =====
    # Non-basic utility functions

    # ===== END UTILITY =====
        
# end class DatabaseManager

def main():
    # Test some stuff!
    print("hey :) main in database_manager")
    db_manager = DatabaseManager()
    # Write into the predicates table
    #row_data = ('test', 'testing', 'is', 'pog', 1.0)
    #insert_result = db_manager.insert_row('predicates', row_data)
    #print("Insert success: " + str(insert_result))
    
    # Write into the concepts table
    #row_data = ('test', 0)
    #insert_result = db_manager.insert_row('concepts', row_data)
    #print("Insert success: " + str(insert_result))
    # Delete from the concepts table
    #delete_result = db_manager.delete_row('concepts', 'name', "'" + 'test' + "'")
    #print("Delete success: " + str(delete_result))
    # Select from the concepts table
    select_results = db_manager.select_row('embeddings', ['name'], ['dog'])
    print("Select results: " + str(select_results))

    #select_results = db_manager.select_row('predicates', ('source', 'target'), ('dog', 'pet'))
    #print("Select results: " + str(select_results))
# end main

if __name__ == '__main__':
    main()
